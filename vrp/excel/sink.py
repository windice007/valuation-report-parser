import json
from time import perf_counter
from vrp import Args
from vrp.base.logger import logger
from sqlalchemy import (
    Table, create_engine, MetaData, String, Text, Enum, CHAR, Numeric, Float,
    and_, cast, column, select, values,
)
from sqlalchemy.engine import Connection
from vrp.base import TABLE_NAME, CaseDict, ValuationReportData
from vrp.excel.utils import obj_json_default
from sqlalchemy.engine.url import make_url, URL
from vrp.storage.batching import rows_per_batch
from vrp.storage.settings import get_db_connection_url


class Sink(object):
    def save(self, vpd: ValuationReportData):
        pass


class FileSink(Sink):
    def save(self, vpd: ValuationReportData):
        file = vpd.file
        with open(f"{file}.json", "w", encoding="utf-8") as writer:
            json.dump(
                {"positions": vpd.details, "products": vpd.products},
                writer,
                default=obj_json_default,
                indent=2,
                ensure_ascii=False,
            )
        logger.info(f"估值数据写入文件完成")


class DbSink(Sink):
    def __init__(self, connection_url: str, batch_size: int = 1000):
        super().__init__()
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        self.batch_size = batch_size
        url: URL = make_url(connection_url)
        backend = url.get_backend_name()

        if backend == "postgresql" or backend == "opengauss":
            schema_name = "schema"
            options_name = "options"
            options_value = ""
            if schema_name in url.query:
                schema_value = url.query[schema_name].strip()
                url = url.difference_update_query([schema_name])

                if len(schema_value) > 0:
                    if options_name in url.query:
                        options_value = url.query[options_name].strip()

                    options_value = options_value + " -c search_path=" + schema_value
                    url = url.update_query_pairs(
                        [
                            (
                                options_name,
                                options_value.strip(),
                            )
                        ]
                    )

        self.engine = create_engine(url)
        self.meta_data = MetaData()

    def get_table(self, table_name: str) -> Table:
        if self.db_type == "oracle":
            table_name = table_name.lower()
        table = self.meta_data.tables.get(table_name)
        if table is not None:
            return table
        return Table(table_name, self.meta_data, autoload_with=self.engine)

    @property
    def db_type(self) -> str:
        return self.engine.name

    def update_or_insert_record(self, con: Connection, record: CaseDict):
        table = self.get_table(record[TABLE_NAME])
        keys = table.primary_key.columns.keys()
        rowcount = -1

        if len(keys) > 0:
            exp = table.update()
            for key in keys:
                exp = exp.where(table.c[key] == record[key])
            result = con.execute(exp, record)
            rowcount = result.rowcount

        if rowcount > 0:
            return

        if self.db_type == "oracle":
            con.execute(table.insert(), record.to_lower_dict())
        else:
            con.execute(table.insert(), record)

    @staticmethod
    def _batch_key(table, row):
        key = []
        for col in table.primary_key.columns:
            value = row[col.key]
            try:
                expected_type = col.type.python_type
            except NotImplementedError:
                return None
            # Database coercion can make Python-distinct keys compare equal.
            # Keep the legacy path for such keys instead of silently reordering
            # their updates or changing the original WHERE comparison.
            if (
                type(value) is not expected_type
                or isinstance(col.type, (CHAR, Numeric))
                or (expected_type is str and not isinstance(col.type, String))
                or getattr(col.type, "collation", None)
            ):
                return None
            key.append(value)
        key = tuple(key)
        try:
            hash(key)
        except TypeError:
            return None
        return key

    def _postgresql_batches(self, records):
        """Keep input order, splitting on shape changes and repeated primary keys."""
        current_table = None
        current_fields = None
        batch = []
        seen = set()
        for record in records:
            table = self.get_table(record[TABLE_NAME])
            # Use reflected column names, not CaseDict's original key casing.
            row = {c.key: record[c.key] for c in table.columns if c.key in record}
            fields = tuple(row)
            key = self._batch_key(table, row)
            if key is None:
                if batch:
                    yield current_table, batch
                    batch = []
                    seen.clear()
                yield table, [row]
                continue
            limit = rows_per_batch(max(1, len(fields)), self.batch_size)
            if batch and (
                table is not current_table
                or fields != current_fields
                or len(batch) >= limit
                or (key and key in seen)
            ):
                yield current_table, batch
                batch = []
                seen.clear()
            current_table, current_fields = table, fields
            batch.append(row)
            if key:
                seen.add(key)
        if batch:
            yield current_table, batch

    def _save_postgresql_batch(self, con: Connection, table: Table, rows: list):
        if self._batch_key(table, rows[0]) is None:
            self.update_or_insert_record(con, CaseDict({TABLE_NAME: table.key, **rows[0]}))
            return
        if not table.primary_key.columns:
            if not rows[0]:
                # DEFAULT VALUES has no multi-row form.
                for _ in rows:
                    con.execute(table.insert().values())
            else:
                con.execute(table.insert().values(rows))
            return

        fields = tuple(rows[0])

        def source_type(name):
            data_type = table.c[name].type
            # Casting to VARCHAR(n) would silently truncate overlong input before
            # the destination can enforce its length constraint.
            if isinstance(data_type, String) and not isinstance(data_type, Enum):
                return Text()
            if isinstance(data_type, Numeric) and not isinstance(data_type, Float):
                return Numeric()
            return data_type

        # Cast columns once rather than constructing a Cast expression for every
        # cell. This also handles an all-NULL VALUES column (inferred as text).
        incoming = values(
            *(column(name, source_type(name)) for name in fields),
            name="vrp_values",
        ).data([tuple(row[name] for name in fields) for row in rows])
        source = select(*(
            cast(incoming.c[name], source_type(name)).label(name) for name in fields
        )).subquery("vrp_source" if table.name != "vrp_source" else "vrp_source_1")
        match = and_(*(c == source.c[c.key] for c in table.primary_key.columns))
        updates = {
            name: source.c[name] for name in fields
            if name not in table.primary_key.columns
        }
        if not updates:
            key = next(iter(table.primary_key.columns))
            updates[key.key] = source.c[key.key]
        con.execute(table.update().where(match).values(updates))

        # Unlike INSERT ... ON CONFLICT, this accepts partial updates to existing
        # rows even when omitted columns have NOT NULL constraints and no default.
        exists = select(1).select_from(table).where(match).correlate(source).exists()
        missing = select(*(source.c[name] for name in fields)).where(~exists)
        con.execute(table.insert().from_select(fields, missing, include_defaults=False))

    def save(self, vpd: ValuationReportData):
        if self.engine is None:
            return
        started = perf_counter()
        batches = 0
        with self.engine.begin() as con:
            for records in (vpd.details, vpd.products):
                if self.db_type == "postgresql":
                    for table, rows in self._postgresql_batches(records):
                        self._save_postgresql_batch(con, table, rows)
                        batches += 1
                else:
                    for record in records:
                        self.update_or_insert_record(con, record)
                        batches += 1
        logger.info(
            "估值数据写入数据库完成，记录%d条，批次%d个，耗时%.3f秒",
            len(vpd.details) + len(vpd.products), batches, perf_counter() - started,
        )


def check_db_settings(args: Args) -> DbSink | None:
    db_url = get_db_connection_url(args)
    if db_url:
        logger.info(f"目标数据库为：{db_url}")
        return DbSink(db_url)
    else:
        logger.warn(
            f"目标数据库配置未找到，请检查参数--connection_url 或者 settings.ini"
        )


class MultiSink(Sink):
    def __init__(self, args: Args) -> None:
        super().__init__()
        self.db_sink = check_db_settings(args)
        self.file_sink = None
        if not args.nofile:
            self.file_sink = FileSink()

    def save(self, vpd: ValuationReportData):
        if self.db_sink:
            self.db_sink.save(vpd)
        if self.file_sink:
            self.file_sink.save(vpd)
