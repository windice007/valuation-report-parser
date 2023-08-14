from vrp.excel.sink import MultiSink
from vrp import Args
from vrp.excel.define import ExcelConfig


from vrp.base.logger import logger
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.sql.expression import Select
from vrp.model.mysql_models import INDICBASESTOCKPOSDTL
import datetime


class Env:
    engine: Engine


def _select(*args, **kw) -> Select:
    return select(*args, **kw)


def fetch_positions(env: Env, product_code: str):
    with Session(env.engine) as session:
        stmt = (
            _select(INDICBASESTOCKPOSDTL)
            .where(INDICBASESTOCKPOSDTL.PRD_CODE == product_code)
            .order_by(INDICBASESTOCKPOSDTL.BIZ_DATE)
        )
        result: list[INDICBASESTOCKPOSDTL] = session.execute(stmt).scalars().all()
    return result


def build_trade(p1: INDICBASESTOCKPOSDTL, p2: INDICBASESTOCKPOSDTL, date):
    if p1 is None:
        return f"{date} buy {p2.SECU_CODE} {p2.POS_QTY}"
    elif p2 is None:
        return f"{date} sell {p1.SECU_CODE} {p1.POS_QTY}"
    else:
        qty = p1.POS_QTY - p2.POS_QTY
        if qty > 0:
            return f"{date} sell {p1.SECU_CODE} {qty}"
        elif qty < 0:
            return f"{date} buy {p1.SECU_CODE} {-qty}"
    return None


def pos_compare(
    start: list[INDICBASESTOCKPOSDTL],
    stop: list[INDICBASESTOCKPOSDTL],
    date: datetime.date,
):
    result = []
    for p1 in start:
        p2 = next((x for x in stop if x.SECU_CODE == p1.SECU_CODE), None)
        trade = build_trade(p1, p2, date)
        if trade:
            result.append(trade)

    for p2 in stop:
        p1 = next((x for x in start if x.SECU_CODE == p1.SECU_CODE), None)
        if p1 is None:
            trade = build_trade(p1, p2, date)
            if trade:
                result.append(trade)
    return result


def insert_trades(results: list):
    logger.info(results)


def handle_product(env: Env, product_code: str):
    positions = fetch_positions(env, product_code)
    logger.info(f"获取产品[{product_code}]持仓：{len(positions)}条记录")

    pos_group: dict[datetime.date, list[INDICBASESTOCKPOSDTL]] = {}

    for p in positions:
        if p.BIZ_DATE not in pos_group:
            pos_group[p.BIZ_DATE] = []
        array = pos_group[p.BIZ_DATE]
        array.append(p)

    dates = list(pos_group.keys())

    results = []
    for i in range(len(dates) - 1):
        start = dates[i]
        stop = dates[i + 1]
        logger.info(f"处理{start}的持仓到{stop}的持仓。")
        results.extend(pos_compare(pos_group.get(start), pos_group.get(stop), stop))

    insert_trades(results)


def process(files: list[str], config: ExcelConfig, args: Args, sink: MultiSink):
    products = ["3212"]
    env: Env = Env()
    env.engine = sink.db_sink.engine
    for code in products:
        handle_product(env, code)
