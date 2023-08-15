from decimal import Decimal
from typing import Any, Callable, Protocol
from typing_extensions import Self
from vrp.excel.sink import MultiSink
from vrp import Args
from vrp.excel.define import ExcelConfig


from vrp.base.logger import logger
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from sqlalchemy.engine import Engine
from sqlalchemy.sql.expression import Select
from vrp.model.mysql_models import (
    INDICBASESTOCKPOSDTL,
    INDICBASEBONDPOSDTL,
    INDICBASETXSTOCK,
    INDICBASETXBOND,
)
import datetime


POSTYPE = INDICBASESTOCKPOSDTL | INDICBASEBONDPOSDTL
TRADETYPE = INDICBASETXSTOCK | INDICBASETXBOND


class Env:
    engine: Engine
    model: POSTYPE
    target_model: TRADETYPE
    trade_builder: Callable[[Self, POSTYPE, POSTYPE, datetime.date], TRADETYPE | None]
    product_code: str


def _select(*args, **kw) -> Select:
    return select(*args, **kw)


def fetch_positions(env: Env) -> list[POSTYPE]:
    model = env.model
    with Session(env.engine) as session:
        stmt = (
            _select(model)
            .where(model.PRD_CODE == env.product_code)
            .order_by(model.BIZ_DATE)
        )
        result: list[POSTYPE] = session.execute(stmt).scalars().all()
    return result


def build_trades(
    env: Env,
    p1: POSTYPE,
    p2: POSTYPE,
    date: datetime.date,
):
    qty = 0
    direction = "buy"
    if p1 is None:
        qty = p2.POS_QTY
        direction = "buy"
    elif p2 is None:
        qty = p1.POS_QTY
        direction = "sell"
    else:
        qty = p1.POS_QTY - p2.POS_QTY
        if qty > 0:
            direction = "sell"
        elif qty < 0:
            direction = "buy"
        qty = abs(qty)

    if qty > 0:
        p: POSTYPE = p1
        t: TRADETYPE = env.target_model()

        t.PRD_CODE = p.PRD_CODE
        t.PORT_CODE = p.PORT_CODE
        t.AST_UNIT_CODE = p.AST_UNIT_CODE
        t.TX_DATE = date
        t.SYMBOL = p.SYMBOL
        t.SECU_CODE = p.SECU_CODE
        t.SECU_NAME = p.SECU_NAME
        t.EXR = getattr(p, "EXR", None)
        t.TX_MKT_CODE = p.TX_MKT_CODE
        t.TRAN_QTY = qty
        t.CUR_CODE = p.CUR_CODE
        t.STRGY_CODE = p.STRGY_CODE
        t.SUB_ACCT_CODE = p.SUB_ACCT_CODE
        t.SECU_TYPE_CODE = p.SECU_TYPE_CODE
        t.TX_FEE = p.TX_FEE
        t.TRAN_NUM = f"GEN_{date.strftime('%Y%m%d')}_{t.SECU_CODE}_{t.PRD_CODE}"
        t.INSTR_NUM = t.TRAN_NUM
        t.CREATE_TIME = p.CREATE_TIME
        t.UPDATE_TIME = p.UPDATE_TIME

        if isinstance(t, INDICBASETXSTOCK):
            t.TRAN_PRC = p.VAL_PRC
            t.TRAN_AMT = t.TRAN_QTY * t.TRAN_PRC
            t.TX_TYPE_CODE = (
                "T01.01.000.001" if direction == "buy" else "T01.01.000.002"
            )
        elif isinstance(t, INDICBASETXBOND):
            t.TRAN_NET_PRC = p.VAL_PRC
            t.TRAN_NET_AMT = t.TRAN_QTY * t.TRAN_NET_PRC
            t.TX_TYPE_CODE = (
                "T02.02.000.001" if direction == "buy" else "T02.02.000.002"
            )

        return t


def pos_compare(
    env: Env, start: list[POSTYPE], stop: list[POSTYPE], date: datetime.date
):
    result = []
    for p1 in start:
        p2 = next((x for x in stop if x.SECU_CODE == p1.SECU_CODE), None)
        trade = env.trade_builder(env, p1, p2, date)
        if trade:
            result.append(trade)

    for p2 in stop:
        p1 = next((x for x in start if x.SECU_CODE == p1.SECU_CODE), None)
        if p1 is None:
            trade = env.trade_builder(env, p1, p2, date)
            if trade:
                result.append(trade)
    return result


def insert_trades(env: Env, results: list):
    count = len(results)
    if count == 0:
        return
    logger.info(f"共生成{count}条交易，写入数据库中...")
    with Session(env.engine) as session:
        stmt = delete(env.target_model).where(
            env.target_model.PRD_CODE == env.product_code
        )
        session.execute(stmt)
        session.add_all(results)
        session.commit()

    logger.info(f"数据库写入完成。")


def handle_product(env: Env):
    positions: list[POSTYPE] = fetch_positions(env)
    logger.info(
        f"获取产品[{env.product_code}][{env.model.__tablename__}]持仓：{len(positions)}条记录"
    )

    pos_group: dict[datetime.date, list[POSTYPE]] = {}

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
        results.extend(
            pos_compare(env, pos_group.get(start), pos_group.get(stop), stop)
        )

    insert_trades(env, results)


def process(files: list[str], config: ExcelConfig, args: Args, sink: MultiSink):
    products = ["3212", "3512", "4523", "541401", "585004", "604310", "611607"]
    # products = ["585004"]
    env: Env = Env()
    env.engine = sink.db_sink.engine
    for code in products:
        env.product_code = code
        env.trade_builder = build_trades

        env.model = INDICBASESTOCKPOSDTL
        env.target_model = INDICBASETXSTOCK
        handle_product(env)

        env.model = INDICBASEBONDPOSDTL
        env.target_model = INDICBASETXBOND
        handle_product(env)
