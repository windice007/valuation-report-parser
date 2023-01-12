

from configparser import ConfigParser
import json

from sqlalchemy import delete
from base.db_mysql import init_db, obj_json_default, session
from excel.process import ValuationReportData
from base.logger import logger
from sqlalchemy.orm.session import Session
from model.mysql_models import VALUATIONPORTIND, VALUATIONPORTPOSDTL, INDICBASEPORTPOSDTL


def save_result_to_file(vpd: ValuationReportData, file: str):
    with open(f'{file}.json', 'w', encoding="utf-8") as writer:
        json.dump({"positions": list(vpd.details.values()), "product": vpd.product}, writer,  default=obj_json_default,
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


def clear_db_data(vpd: ValuationReportData, con: Session):
    p: VALUATIONPORTIND = vpd.product

    if p.BUSI_DATE is None or p.PRODUCT_CODE is None:
        logger.warn("持仓和产品的必要字段没有配置")
        return

    con.execute(delete(VALUATIONPORTPOSDTL).where(VALUATIONPORTPOSDTL.BUSI_DATE ==
                p.BUSI_DATE, VALUATIONPORTPOSDTL.PRODUCT_CODE == p.PRODUCT_CODE))
    con.execute(delete(VALUATIONPORTIND).where(VALUATIONPORTIND.BUSI_DATE ==
                p.BUSI_DATE, VALUATIONPORTIND.PRODUCT_CODE == p.PRODUCT_CODE))
    con.execute(delete(INDICBASEPORTPOSDTL).where(INDICBASEPORTPOSDTL.BIZ_DATE ==
                p.BUSI_DATE, INDICBASEPORTPOSDTL.PRD_CODE == p.PRODUCT_CODE))


def save_result_to_db(vpd: ValuationReportData, file: str):
    con = session()
    if con is None:
        logger.warn("无法获取数据库信息，估值数据无法写入数据库")
        return
    try:

        clear_db_data(vpd, con)

        con.add_all(list(vpd.details.values()))
        con.add(vpd.product)

        con.commit()
        logger.info(f"估值数据写入数据库完成")
    except Exception as ex:
        logger.error(ex)
        con.rollback()

    con.close()
