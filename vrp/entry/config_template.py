"""根据数据库中表字段，生成估值表解析配置模板。"""
from argparse import ArgumentParser
from typing import Protocol
from vrp.excel.define import (
    ExcelConfig,
    GroupDefine,
    HandlerDefine,
    PositionDefine,
    ProductDefine,
)
from vrp.excel.sink import check_db_settings, obj_json_default
from vrp.excel.utils import Dict
import json
from sqlalchemy import Table, Column, Date, DateTime, String, Numeric
import datetime
from configparser import RawConfigParser
from vrp.base.logger import logger
import os


class Args(Protocol):
    connection_url: str
    position_tables: str
    product_tables: str
    dir: str


def set_parser(parser: ArgumentParser):
    parser.add_argument("--connection_url", default="", type=str, help="指定目标数据库的链接字符串")
    parser.add_argument("--position_tables", default=None, type=str, help="指定目标持仓表清单")
    parser.add_argument("--product_tables", default=None, type=str, help="指定目标产品指标表")


def table_dict(table: Table):
    result = {}

    for v in table.columns:
        col: Column = v
        col_type = type(col.type)
        if not col.nullable:
            if issubclass(col_type, Date):
                result[col.key] = datetime.datetime.now().strftime("%Y-%m-%d")
            elif issubclass(col_type, DateTime):
                result[col.key] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elif issubclass(col_type, Numeric):
                result[col.key] = 0
            elif issubclass(col_type, String):
                result[col.key] = ""
        else:
            result[col.key] = None
    return result


def process(args: Args):
    args.dir = "."
    dbsink = check_db_settings(args)

    if dbsink is None:
        logger.error(f"目标数据库配置未找到，模板生成失败！")
        return

    config: ExcelConfig = Dict()
    config.subject_code_column = "A"

    if isinstance(args.position_tables, str):
        position_tables = args.position_tables.split(",")
        if len(position_tables) > 0:
            config.positions = []
            for table in position_tables:
                p: PositionDefine = Dict()
                p.table = table
                p.groups = []
                g: GroupDefine = Dict()
                g.handlers = []
                h: HandlerDefine = Dict()
                h.subject_filter_regex = ".+"
                h.values = table_dict(dbsink.get_table(table))
                g.handlers.append(h)
                p.groups.append(g)
                config.positions.append(p)

    if isinstance(args.product_tables, str):
        product_tables = args.product_tables.split(",")
        if len(product_tables):
            config.products = []
            for table in product_tables:
                prod: ProductDefine = Dict()
                prod.table = table
                prod.values = table_dict(dbsink.get_table(table))
                config.products.append(prod)

    config_file = "config.json"

    with open(config_file, encoding="utf-8", mode="w") as f:
        json.dump(config, f, default=obj_json_default, ensure_ascii=False, indent=2)

    logger.info(f"生成配置模板：{config_file} ")

    settings = "settings.ini"

    if (
        isinstance(args.connection_url, str)
        and args.connection_url != ""
        and not os.path.exists(settings)
    ):
        with open(settings, encoding="utf-8", mode="w") as f:
            section = "database"
            cp = RawConfigParser()
            cp.add_section(section)
            cp.set(section, "connection_url", args.connection_url)
            cp.write(f, False)

        logger.info(f"生成配置文件：{settings} ")
