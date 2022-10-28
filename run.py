from configparser import ConfigParser
import json

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

__version__ = "0.1.1"


def current_dir_files():
    result = glob.glob("*.xls")+glob.glob("*.xlsx")
    return list(filter(lambda x: not x.startswith("~$"), result))


def save_result_to_file(vpd: ValuationReportData, file: str):
    with open(f'{file}.json', 'w', encoding="utf-8") as writer:
        json.dump({"positions": list(vpd.details.values()), "product": vpd.product}, writer,  default=obj_json_default,
                  indent=2, ensure_ascii=False)


def save_result_to_db(vpd: ValuationReportData, file: str, session):
    pass


def get_db_connection_url(args: object):
    if args.connection_url != '':
        return args.connection_url
    cp = ConfigParser()
    cp.read('settings.ini')
    if cp.has_option("database", "connection_url"):
        return cp.get("database", "connection_url")
    return None


def main():
    parser = argparse.ArgumentParser(description="估值表解析程序")
    parser.add_argument("-v", "--version", action="version",
                        version=__version__, help="display app version.")
    parser.add_argument("-d", "--dir", default=".", type=str,
                        help="指定工作目录，程序会在工作目录中检索可用的估值表文件。如果不设定，默认为当前工作目录。")
    parser.add_argument("--connection_url", default="", type=str,
                        help="指定目标数据库的链接字符串")

    args = parser.parse_args()

    os.chdir(args.dir)

    db_url = get_db_connection_url(args)
    DbSession = None
    if db_url:
        logger.info(f"目标数据库为：{db_url}")
        DbSession = init_db(db_url)
    else:
        logger.warn(f"目标数据库配置未找到，请检查参数--connection_url 或者 settings.ini")

    with open('config.json', 'r', encoding="utf-8") as f:
        config = json.load(f, object_hook=obj_json_hook)

        files = current_dir_files()

        if len(files) == 0:
            print("指定工作目录没有找到估值文件(*.xls|*.xlsx)")

        for file in current_dir_files():
            vpd = process(file, config)
            save_result_to_file(vpd, file)
            if DbSession:
                save_result_to_db(vpd, file, DbSession())


if __name__ == "__main__":
    main()
