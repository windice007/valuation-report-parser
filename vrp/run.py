"""
valuation report parser
"""
from io import TextIOBase
import json
import logging
from vrp.base.utils import search_app_file
from vrp.excel.define import ExcelConfig

from vrp.excel.process import process
from vrp.excel.utils import Dict, obj_json_hook

# hidden import
import pyexcel_xls
import pyexcel_xlsx
import pyexcel_io.readers
import pyexcel_io.writers
from cryptography.hazmat.primitives.kdf import pbkdf2
import opengauss_sqlalchemy.psycopg2

import os
import argparse
from vrp.base.logger import logger
from vrp.excel.sink import MultiSink
from vrp import Args, __version__
import time


def excel_filter(file):
    if not os.path.isfile(file):
        return False
    file_name: str = os.path.basename(file)
    if file_name.startswith("~$"):
        return False
    return file_name.lower().endswith((".xls", ".xlsx", ".csv"))


def current_dir_files(dir):
    result = map(lambda x: os.path.join(dir, x), os.listdir(dir))
    return list(filter(excel_filter, result))


def init_config(config: ExcelConfig):
    if config.subject_code_column is None:
        config.subject_code_column = "A"
    return config


def load_config_file(args: Args):
    if isinstance(args.config, TextIOBase):
        config: ExcelConfig = json.loads(args.config.read(), object_hook=obj_json_hook)
        return init_config(config)

    file = search_app_file(args.config, args.dir)
    if file is None:
        return None

    logger.info(f"加载配置文件：{os.path.abspath(file)}")

    with open(file, "r", encoding="utf-8") as f:
        config: ExcelConfig = json.load(f, object_hook=obj_json_hook)
    return init_config(config)


def process_file(
    file: str,
    config: str = "config.json",
    connection_url: str = None,
    nofile: bool = False,
    debug: bool = False,
):
    """
    这个函数用来处理估值表文件

    :param file: 估值表文件路径，该路径也可以是一个目录，程序会处理目录中所有的估值表文件（.xls和.xlsx）
    :param config: 该估值表解析配置文件，一般都是json文件。如果不设置，程序会自动检索。
    :param connection_url: 目标数据库的连接字符串,格式遵循SQLAlchemy规范。例如:mysql+pymysql://user:passwd@10.10.20.100:3306/database。如果不设置，程序会自动检索settings.ini文件，读取其中connection_url的值。
    :param debug: 默认为False，如果设置为True,会显示更多信息。
    :param nofile: 默认为False，如果设置为True，将不会生成本地结果文件。

    自动检索说明：首先会检索估值表文件所在的目录，其次会检索当前工作目录，查找对应的配置文件进行加载。
    """
    args: Args = Dict()
    args.config = config
    args.dir = file
    args.connection_url = connection_url
    args.debug = debug
    args.nofile = nofile

    do_job(args)


def do_job(args: Args):
    app_start_time = time.time()

    dest_file = args.dir if os.path.isfile(args.dir) else None
    if dest_file is not None:
        args.dir = os.path.dirname(args.dir)

    logger.info(f"工作目录为：{os.path.abspath(args.dir)}")

    config: ExcelConfig = load_config_file(args)
    sink = MultiSink(args)

    if dest_file is None:
        files = current_dir_files(args.dir)
    else:
        files = [dest_file]

    if len(files) == 0:
        logger.warning("指定工作目录没有找到估值文件(*.xls|*.xlsx)")

    process(files, config, args, sink)
    logger.info(f"程序处理完成，共耗时{round(time.time()-app_start_time,3)}秒。")


def main():
    parser = argparse.ArgumentParser(description="估值表解析程序")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
        help="display app version.",
    )
    parser.add_argument(
        "dir",
        nargs="?",
        default=".",
        type=str,
        help="指定工作目录，程序会在工作目录中检索可用的估值表文件。如果不设定，默认为当前工作目录。",
    )
    parser.add_argument(
        "-c", "--config", default="config.json", type=str, help="指定配置文件"
    )
    parser.add_argument("--connection_url", default="", type=str, help="指定目标数据库的链接字符串")
    parser.add_argument("--nofile", action="store_true", default=False, help="不生成结果文件。")
    parser.add_argument(
        "--debug", action="store_true", default=False, help="启用debug模式，会输出更多信息。"
    )

    args: Args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.info(f"{parser.description} {__version__}")
    do_job(args)


if __name__ == "__main__":
    main()
