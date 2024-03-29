from configparser import RawConfigParser
import json
import os
from vrp import Args
from vrp.base.logger import logger
from sqlalchemy import Table, create_engine, MetaData
from sqlalchemy.engine import Connection
from vrp.base import TABLE_NAME, CaseDict, ValuationReportData
from vrp.base.utils import search_app_file
from vrp.excel.utils import obj_json_default
from sqlalchemy.engine.url import make_url, URL


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
    def __init__(self, connection_url: str):
        super().__init__()
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

    def save(self, vpd: ValuationReportData):
        if self.engine is None:
            return
        with self.engine.begin() as con:
            for record in vpd.details:
                self.update_or_insert_record(con, record)
            for record in vpd.products:
                self.update_or_insert_record(con, record)
        logger.info(f"估值数据写入数据库完成")


def get_db_connection_url(args: Args):
    if isinstance(args.connection_url, str) and args.connection_url != "":
        return args.connection_url
    cp = RawConfigParser()
    settings_file = search_app_file("settings.ini", args.dir)
    if settings_file:
        logger.info(f"加载配置文件：{os.path.abspath(settings_file)}")
        cp.read(settings_file)
        if cp.has_option("database", "connection_url"):
            return cp.get("database", "connection_url")
    return None


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
