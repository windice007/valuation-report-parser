"""
valuation report parser
"""
from datetime import datetime
import json
import logging

from vrp.excel.process import process_excel_file_data as process
from vrp.excel.utils import obj_json_hook

# hidden import
import pyexcel_xls
import pyexcel_xlsx
import pyexcel_io.writers
from cryptography.hazmat.primitives.kdf import pbkdf2

import os
import glob
import argparse
from vrp.base.logger import logger
from vrp.excel.sink import FileSink, check_db_settings
import pyexcel
from vrp.base import ENV_FILE_NAME, ENV_PROCESS_TIME, ENV_DB_SINK, ENV_DEBUG
from vrp import __version__


def current_dir_files():
    result = glob.glob("*.xls") + glob.glob("*.xlsx")
    return list(filter(lambda x: not x.startswith("~$"), result))


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

    logger.debug(f"工作目录为：{os.path.abspath(args.dir)}")
    db_sink = check_db_settings(args)
    file_sink = FileSink()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f, object_hook=obj_json_hook)

        files = current_dir_files()

        if len(files) == 0:
            print("指定工作目录没有找到估值文件(*.xls|*.xlsx)")

        for file in current_dir_files():
            logger.info(f"开始处理估值文件：{file}")
            vpd = process(
                pyexcel.get_sheet(file_name=file),
                config,
                {
                    ENV_FILE_NAME: file,
                    ENV_PROCESS_TIME: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ENV_DB_SINK: db_sink,
                    ENV_DEBUG: args.debug,
                },
            )

            file_sink.save(vpd, file_name=file, debug=args.debug)
            if db_sink is not None:
                db_sink.save(vpd)


if __name__ == "__main__":
    main()
