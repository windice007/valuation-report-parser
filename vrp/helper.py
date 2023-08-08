"""
helper
"""
import json
import logging
from vrp.base.utils import excel_column_index
from vrp.excel.define import ExcelConfig

from vrp.excel.utils import obj_json_hook

import os
import glob
import argparse
from vrp.base.logger import logger
from vrp import __version__
import time

import pyexcel
import re


def current_dir_files():
    result = glob.glob("*.xls") + glob.glob("*.xlsx")
    return list(filter(lambda x: not x.startswith("~$"), result))


def load_config_file(args):
    with open(args.config, "r", encoding="utf-8") as f:
        config: ExcelConfig = json.load(f, object_hook=obj_json_hook)
    return config


def main():
    parser = argparse.ArgumentParser(description="估值表解析协助程序")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
        help="display app version.",
    )
    parser.add_argument(
        "-d",
        "--dir",
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

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    os.chdir(args.dir)

    logger.info(f"{parser.description} {__version__}")

    logger.info(f"工作目录为：{os.path.abspath(args.dir)}")

    config: ExcelConfig = load_config_file(args)
    logger.info(f"加载配置文件：{os.path.abspath(args.config)}")

    files = current_dir_files()

    if len(files) == 0:
        print("指定工作目录没有找到估值文件(*.xls|*.xlsx)")

    result = {}

    for file in current_dir_files():
        process_excel_file(file, config, result)

    records = list(result.values())
    pyexcel.save_as(records=records, dest_file_name="../code.xlsx")


def process_excel_file(file, config: ExcelConfig, result: dict):
    logger.info(f"开始处理估值文件：{file}")
    sheet = pyexcel.get_sheet(file_name=file, sheet_name=config.sheet_name)

    for i in range(len(sheet)):
        code = sheet.cell_value(i, excel_column_index(config.subject_code_column))
        if code == "" or code == None:
            continue
        name = sheet.cell_value(i, excel_column_index("B"))

        if re.fullmatch("\\d{4,}", code):
            result[code] = {
                "code": code,
                "name": name,
                "file": file,
                "is": len(code) == 14,
            }


if __name__ == "__main__":
    start_time = time.time()
    main()
    logger.info(f"程序处理完成，共耗时{round(time.time()-start_time,3)}秒。")
