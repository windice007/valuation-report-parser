from sqlalchemy import Engine, Table, create_engine, MetaData, DECIMAL

from base import TABLE_NAME, ValuationReportData
from base.logger import logger


class MySQLTableSink:
    meta_data = MetaData()

    def __init__(self, engine: Engine, table: str) -> None:
        self._engine = engine
        self.table = Table(table, MySQLTableSink.meta_data,
                           autoload_with=self._engine)
        self.schema = self._engine.url.database

        self._primary_columns = None

    def column_schema(self, column: str):
        return self.table.columns.get(column)

    def has_column(self, column: str):
        return column in self.table.columns

    def is_decimal(self, column: str):
        if not self.has_column(column):
            return False
        column_schema = self.column_schema(column)
        return isinstance(column_schema.type, DECIMAL)

    @property
    def primary_columns(self):
        if self._primary_columns is None:
            self._primary_columns = []
            for k, c in self.table.columns.items():
                if c.primary_key:
                    self._primary_columns.append(k)
        return self._primary_columns


__sinks__: dict[str, MySQLTableSink] = {}


def get_table_sink(table: str):
    if table not in __sinks__:
        __sinks__[table] = MySQLTableSink(DB_ENGINE, table)
    return __sinks__.get(table)


DB_ENGINE: Engine = None


def init_db(connection_url: str):
    global DB_ENGINE
    DB_ENGINE = create_engine(connection_url)


def make_expression(sink: MySQLTableSink, record: dict):
    table = sink.table
    exp = table.update()
    for key in sink.primary_columns:
        exp = exp.where(table.c[key] == record[key])
    return exp


def save_result_to_db(vpd: ValuationReportData):
    if DB_ENGINE is None:
        return
    with DB_ENGINE.begin() as con:
        for record in vpd.details:
            sink = get_table_sink(record[TABLE_NAME])
            con.execute(make_expression(sink, record), record)
        if vpd.product:
            sink = get_table_sink(vpd.product[TABLE_NAME])
            con.execute(make_expression(sink, vpd.product), vpd.product)
    logger.info(f"估值数据写入数据库完成")
