from vrp.excel.sink import MultiSink
from vrp import Args
from vrp.excel.define import ExcelConfig


from vrp.base.logger import logger
from sqlalchemy.orm import Session


def process(files: list[str], config: ExcelConfig, args: Args, sink: MultiSink):
    table_pos = sink.db_sink.get_table("VALUATION_PORT_POS_DTL")
    with Session(sink.db_sink.engine) as session:
        result = session.execute(table_pos.select()).all()

        logger.info(len(result))

    logger.info(table_pos)
