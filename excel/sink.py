from configparser import ConfigParser
import decimal
import json
from base.logger import logger
from sqlalchemy import Engine, Table, create_engine, MetaData, DECIMAL
from base import TABLE_NAME, ValuationReportData


class Sink(object):
    def save(self, vpd: ValuationReportData, **keyargs):
        pass


def obj_json_default(obj):
    if type(obj) is decimal.Decimal:
        return float(obj)
    return obj


class FileSink(Sink):
    def save(self, vpd: ValuationReportData, **keyargs):
        file = keyargs['file_name']
        with open(f'{file}.json', 'w', encoding="utf-8") as writer:
            json.dump({"positions": vpd.details, "product": vpd.product}, writer, default=obj_json_default,
                      indent=2, ensure_ascii=False)
        logger.info(f"估值数据写入文件完成")


class DbSink(Sink):
    def __init__(self, connection_url: str):
        super().__init__()
        self.engine = create_engine(connection_url)
        self.meta_data = MetaData()

    def get_table(self, table_name: str) -> Table:
        table = self.meta_data.tables.get(table_name)
        if table is not None:
            return table
        return Table(table_name, self.meta_data, autoload_with=self.engine)

    def make_delete_expression(self, table: Table, record: dict):
        exp = table.delete()
        keys = table.primary_key.columns.keys()
        for key in keys:
            exp = exp.where(table.c[key] == record[key])
        return exp

    def save(self, vpd: ValuationReportData, **keyargs):
        if self.engine is None:
            return
        with self.engine.begin() as con:
            for record in vpd.details:
                table = self.get_table(record[TABLE_NAME])
                con.execute(self.make_delete_expression(table, record))
                con.execute(table.insert(), record)
            if vpd.product:
                table = self.get_table(vpd.product[TABLE_NAME])
                con.execute(self.make_delete_expression(table, vpd.product))
                con.execute(table.insert(), vpd.product)
        logger.info(f"估值数据写入数据库完成")


def get_db_connection_url(args: object):
    if args.connection_url != '':
        return args.connection_url
    cp = ConfigParser()
    cp.read('settings.ini')
    if cp.has_option("database", "connection_url"):
        return cp.get("database", "connection_url")
    return None


def check_db_settings(args: object) -> DbSink | None:
    db_url = get_db_connection_url(args)
    if db_url:
        logger.info(f"目标数据库为：{db_url}")
        return DbSink(db_url)
    else:
        logger.warn(f"目标数据库配置未找到，请检查参数--connection_url 或者 settings.ini")
