from configparser import ConfigParser
import json
import logging

from base.db_mysql import obj_json_default
from excel import process_excel_file_data as process
from excel.process import ValuationReportData
from excel.utils import obj_json_hook
import pyexcel_xls
import pyexcel_xlsx
import pyexcel_io.writers
import os
import glob
import argparse
from base.db_mysql import init_db
from base.logger import logger
from excel.sink import check_db_settings, save_result_to_file, save_result_to_db

__version__ = "0.1.14"


def current_dir_files():
    result = glob.glob("*.xls")+glob.glob("*.xlsx")
    return list(filter(lambda x: not x.startswith("~$"), result))


def main():
    parser = argparse.ArgumentParser(description="估值表解析程序")
    parser.add_argument("-v", "--version", action="version",
                        version=__version__, help="display app version.")
    parser.add_argument("-d", "--dir", default=".", type=str,
                        help="指定工作目录，程序会在工作目录中检索可用的估值表文件。如果不设定，默认为当前工作目录。")
    parser.add_argument("--connection_url", default="", type=str,
                        help="指定目标数据库的链接字符串")
    parser.add_argument("--debug", action="store_true", default=False,
                        help="启用debug模式，会输出更多信息。")

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    os.chdir(args.dir)

    logger.info(f"{parser.description} {__version__}")

    logger.debug(f"工作目录为：{os.path.abspath(args.dir)}")
    check_db_settings(args)

    with open('config.json', 'r', encoding="utf-8") as f:
        config = json.load(f, object_hook=obj_json_hook)

        files = current_dir_files()

        if len(files) == 0:
            print("指定工作目录没有找到估值文件(*.xls|*.xlsx)")

        for file in current_dir_files():
            logger.info(f"开始处理估值文件：{file}")
            vpd = process(file, config)
            save_result_to_file(vpd, file)
            save_result_to_db(vpd, file)


if __name__ == "__main__":
    main()
