from vrp.excel.sink import MultiSink
from vrp import Args
from vrp.excel.define import ExcelConfig


from vrp.base.logger import logger
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.sql.expression import Select
from vrp.model.mysql_models import VALUATIONPORTPOSDTL
import datetime


class Env:
    engine: Engine


def _select(*args, **kw) -> Select:
    return select(*args, **kw)


def fetch_positions(env: Env, product_code: str):
    with Session(env.engine) as session:
        stmt = (
            _select(VALUATIONPORTPOSDTL)
            .where(VALUATIONPORTPOSDTL.PRODUCT_CODE == product_code)
            .order_by(VALUATIONPORTPOSDTL.BUSI_DATE)
        )
        result: list[VALUATIONPORTPOSDTL] = session.execute(stmt).scalars().all()
    return result


def build_trade(p1, p2, date):
    ...


def pos_compare(
    start: list[VALUATIONPORTPOSDTL],
    stop: list[VALUATIONPORTPOSDTL],
    date: datetime.date,
):
    result = []
    for p1 in start:
        p2 = next((x for x in stop if x.SECU_CODE == p1.SECU_CODE), None)
        result.append(build_trade(p1, p2, date))

    for p2 in stop:
        p1 = next((x for x in start if x.SECU_CODE == p1.SECU_CODE), None)
        if p1 is None:
            result.append(build_trade(p1, p2, date))

    return result


def handle_product(env: Env, product_code: str):
    positions = fetch_positions(env, product_code)
    logger.info(f"获取产品[{product_code}]持仓：{len(positions)}条记录")

    pos_group: dict[datetime.date, list[VALUATIONPORTPOSDTL]] = {}

    for p in positions:
        if p.BUSI_DATE not in pos_group:
            pos_group[p.BUSI_DATE] = []
        array = pos_group[p.BUSI_DATE]
        array.append(p)

    dates = list(pos_group.keys())

    for i in range(len(dates) - 1):
        start = dates[i]
        stop = dates[i + 1]
        logger.info(f"处理{start}的持仓到{stop}的持仓。")
        pos_compare(pos_group.get(start), pos_group.get(stop), stop)


def process(files: list[str], config: ExcelConfig, args: Args, sink: MultiSink):
    products = ["3212"]
    env: Env = Env()
    env.engine = sink.db_sink.engine
    for code in products:
        handle_product(env, code)
