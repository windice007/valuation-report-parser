from configparser import RawConfigParser
from datetime import datetime, date
import decimal
import json
import os
from vrp import Args
from vrp.base.logger import logger
from sqlalchemy import Table, create_engine, MetaData
from vrp.base import TABLE_NAME, ValuationReportData
from vrp.base.utils import search_app_file
from vrp.excel.utils import Dict
from sqlalchemy.engine.url import make_url, URL


class Sink(object):
    def save(self, vpd: ValuationReportData):
        pass


def obj_json_default(obj):
    if type(obj) is Dict:
        return obj.data
    if type(obj) is decimal.Decimal:
        return float(obj)
    if type(obj) is datetime:
        if obj.hour == 0 and obj.minute == 0 and obj.second == 0:
            return obj.strftime("%Y-%m-%d")
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    if type(obj) is date:
        return obj.strftime("%Y-%m-%d")
    return obj


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
        schema_name = "schema"
        schema_value = None

        if backend == "postgresql" or backend == "opengauss":
            if schema_name in url.query:
                schema_value = url.query[schema_name]
                url = url.difference_update_query([schema_name])

        self.engine = create_engine(url)
        self.meta_data = MetaData(schema=schema_value)

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

    def make_delete_expression(self, table: Table, record: dict):
        exp = table.delete()
        keys = table.primary_key.columns.keys()
        for key in keys:
            exp = exp.where(table.c[key] == record[key])
        return exp

    def save(self, vpd: ValuationReportData):
        if self.engine is None:
            return
        with self.engine.begin() as con:
            for record in vpd.details:
                table = self.get_table(record[TABLE_NAME])
                con.execute(self.make_delete_expression(table, record))
                if self.db_type == "oracle":
                    con.execute(table.insert(), record.to_lower_dict())
                else:
                    con.execute(table.insert(), record)
            for pro in vpd.products:
                table = self.get_table(pro[TABLE_NAME])
                con.execute(self.make_delete_expression(table, pro))
                if self.db_type == "oracle":
                    con.execute(table.insert(), pro.to_lower_dict())
                else:
                    con.execute(table.insert(), pro)
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
        logger.warn(f"目标数据库配置未找到，请检查参数--connection_url 或者 settings.ini")


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
