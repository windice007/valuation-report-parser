from configparser import ConfigParser
import decimal
import json
from base.db_mysql import init_db
from excel.process import ValuationReportData
from base.logger import logger


def obj_json_default(obj):
    if type(obj) is decimal.Decimal:
        return float(obj)
    return obj


def save_result_to_file(vpd: ValuationReportData, file: str):
    with open(f'{file}.json', 'w', encoding="utf-8") as writer:
        json.dump({"positions": vpd.details, "product": vpd.product}, writer, default=obj_json_default,
                  indent=2, ensure_ascii=False)
    logger.info(f"估值数据写入文件完成")


def get_db_connection_url(args: object):
    if args.connection_url != '':
        return args.connection_url
    cp = ConfigParser()
    cp.read('settings.ini')
    if cp.has_option("database", "connection_url"):
        return cp.get("database", "connection_url")
    return None


def check_db_settings(args: object):
    db_url = get_db_connection_url(args)
    if db_url:
        logger.info(f"目标数据库为：{db_url}")
        init_db(db_url)
    else:
        logger.warn(f"目标数据库配置未找到，请检查参数--connection_url 或者 settings.ini")


def clear_db_data(vpd: ValuationReportData):
    pass


def save_result_to_db(vpd: ValuationReportData):
    pass
