"""
valuation report parser
"""
import json
import logging
from vrp.base.utils import search_app_file
from vrp.excel.define import ExcelConfig

from vrp.excel.process import process
from vrp.excel.utils import obj_json_hook

# hidden import
import pyexcel_xls
import pyexcel_xlsx
import pyexcel_io.writers
from cryptography.hazmat.primitives.kdf import pbkdf2
import opengauss_sqlalchemy.psycopg2

import os
import glob
import argparse
from vrp.base.logger import logger
from vrp.excel.sink import MultiSink
from vrp import Args, __version__
import time
import importlib


def excel_filter(file):
    if not os.path.isfile(file):
        return False
    file_name: str = os.path.basename(file)
    if file_name.startswith("~$"):
        return False
    return file_name.endswith(".xls") or file_name.endswith(".xlsx")


def current_dir_files(dir):
    result = map(lambda x: os.path.join(dir, x), os.listdir(dir))
    return list(filter(excel_filter, result))


def load_config_file(args: Args):
    file = search_app_file(args.config, args.dir)
    if file is None:
        raise FileNotFoundError(args.config)

    logger.info(f"加载配置文件：{os.path.abspath(file)}")

    with open(file, "r", encoding="utf-8") as f:
        config: ExcelConfig = json.load(f, object_hook=obj_json_hook)
    return config


def main():
    app_start_time = time.time()
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
    parser.add_argument("--entry", default=None, type=str, help="指定处理程序入口。")

    args: Args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.info(f"{parser.description} {__version__}")

    logger.info(f"工作目录为：{os.path.abspath(args.dir)}")

    config: ExcelConfig = load_config_file(args)
    sink = MultiSink(args)

    files = current_dir_files(args.dir)

    if len(files) == 0:
        print("指定工作目录没有找到估值文件(*.xls|*.xlsx)")

    if args.entry is None:
        process(files, config, args, sink)
    else:
        logger.info(f"处理程序入口为：{args.entry}")
        m = importlib.import_module(f"vrp.entry.{args.entry}")
        entry_process = getattr(m, "process")
        if entry_process and callable(entry_process):
            entry_process(files, config, args, sink)
        else:
            logger.error(f"处理程序入口无法使用：{args.entry}")
    logger.info(f"程序处理完成，共耗时{round(time.time()-app_start_time,3)}秒。")


if __name__ == "__main__":
    main()
