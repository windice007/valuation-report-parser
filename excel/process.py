
from datetime import datetime
import re
from base import DATASOUCE, ENV_DEBUG, TABLE_NAME, CaseDict, ValuationReportData, ENV_DB_SINK
from excel.define import DataCell, ExcelConfig, PositionDefine
from pyexcel.sheet import Sheet
from base.utils import excel_column_index, is_position_column_str, is_position_str
from excel.sink import DbSink
from excel.utils import Dict
from base.logger import logger
from decimal import Decimal
from sqlalchemy import Table, Numeric
from dateutil.parser import parse as parse_date


class ProcessContext:
    sheet: Sheet | None = None
    subject_column: int | None = None
    config: ExcelConfig | None = None
    subject_row_map: dict = {}

    def __init__(self, sheet: Sheet, config: ExcelConfig) -> None:
        self.sheet = sheet
        self.config = config
        self.subject_column = excel_column_index(config.subject_code_column)
        self.env = {}
        self.current_row = -1
        self.current_model = {}
        self.is_debug = False

    def is_oracle(self) -> bool:
        db_sink: DbSink = self.env[ENV_DB_SINK]
        return db_sink.db_type == "oracle"


def capture_data(context: ProcessContext, cell: DataCell, row: int = None) -> str:
    sheet = context.sheet
    if cell == None or cell.address == None:
        return None
    cell_value = None
    if cell.address in context.env:
        cell_value = context.env.get(cell.address)
    elif is_position_str(cell.address):
        cell_value = sheet[cell.address]
    elif is_position_column_str(cell.address):
        column_index = excel_column_index(cell.address)
        subject_code = get_cell_subject_code(context, cell, row)
        if isinstance(subject_code, str):
            if subject_code in context.subject_row_map:
                r = context.subject_row_map[subject_code]
                cell_value = sheet.cell_value(r, column_index)
            else:
                # raise Exception("未找到指定的科目:{}".format(subject_code))
                logger.warn(f"未找到指定的科目:{subject_code}")
        else:
            cell_value = sheet.cell_value(row, column_index)
    else:
        logger.warn(f"DataCell.address 配置不正确：{cell.address}")

    if cell_value is None:
        return None

    if cell.capture_regex != None:
        match = re.search(re.compile(cell.capture_regex), cell_value)
        if match:
            if len(match.groups()) > 0:
                cell_value = match[1]
            else:
                cell_value = match[0]
        else:
            logger.warn(f"未捕获到指定字段：[{cell_value}]@[{cell.capture_regex}]")
            cell_value = None

    if isinstance(cell.mapping, dict) and cell_value in cell.mapping:
        cell_value = cell.mapping.get(cell_value)

    if cell.type == 'number' and isinstance(cell_value, str):
        cell_value = convert_str_to_decimal(cell_value)
    elif cell.type == 'str' and not isinstance(cell_value, str):
        cell_value = str(cell_value)
    return cell_value


def get_cell_subject_code(context: ProcessContext, cell: DataCell, row: int = None) -> str:
    if isinstance(cell.subject_code, Dict):
        return capture_data(context, cell.subject_code, row)
    return cell.subject_code


def convert_str_to_decimal(v: str) -> Decimal:
    v = v.replace(",", "")
    if v == '':
        return Decimal(0)
    elif v.endswith("%"):
        return Decimal(v.rstrip("%"))/100
    else:
        return Decimal(v)


def convert_str_to_date(v: str) -> datetime:
    return parse_date(v)


def custom_eval(formula: str, local: dict):
    if isinstance(local, dict):
        return eval(formula, None, local)
    return eval(formula, None, local.__dict__)


def process_positions(context: ProcessContext, vpd: ValuationReportData):
    config = context.config

    for pos in config.positions:
        logger.debug(f"处理持仓：{pos}")
        handle_position(context, pos, vpd)


def handle_position(context: ProcessContext, pos: PositionDefine, vpd: ValuationReportData):
    sheet = context.sheet
    if not isinstance(pos.groups, list):
        logger.warn(f'没有有效的持仓定义:{pos.table}')
        return
    details = []
    for group in pos.groups:
        if not isinstance(group.handlers, list):
            logger.warn(f'没有有效的处理配置:{pos.table}')
            continue
        for handler in group.handlers:
            for i in range(len(sheet)):
                code = sheet.cell_value(i, context.subject_column)
                if code == '' or code == None:
                    continue
                if re.search(handler.subject_filter_regex, code):
                    context.current_model = create_model(pos.table)
                    if context.is_debug:
                        context.current_model[DATASOUCE] = [code]
                    context.current_row = i
                    process_data(context, pos.default)
                    process_data(context, group.default)
                    process_data(context, handler.values)
                    append_details(context, details, context.current_model)

    vpd.details.extend(details)


def is_same_position(m1: dict, m2: dict, keys: list[str]):
    if m1[TABLE_NAME] != m2[TABLE_NAME]:
        return False
    for key in keys:
        if key not in m1 and key not in m2:
            continue
        if key not in m1 and key in m2:
            return False
        if key in m1 and key not in m2:
            return False
        if m1[key] != m2[key]:
            return False
    return True


class TableProxy(object):
    def __init__(self, table: Table):
        self.table = table

    def keys(self):
        return self.table.columns.keys()

    def get_column(self, name: str):
        if name in self.table.columns:
            return self.table.columns[name]
        for k, v in self.table.columns.items():
            if k.lower() == name.lower():
                return v
        return None

    def is_number(self, name: str):
        column = self.get_column(name)
        return isinstance(column.type, Numeric)

    def is_oracle_date(self, name: str):
        return False


def get_table_schema(context: ProcessContext, table_name: str):
    db_sink: DbSink = context.env[ENV_DB_SINK]
    return TableProxy(db_sink.get_table(table_name)) if db_sink is not None else None


def append_details(context: ProcessContext, details: list, model: dict):
    table: TableProxy = get_table_schema(context, model[TABLE_NAME])

    if table is None:
        details.append(model)
        return

    keys = table.keys()
    target = next(
        (x for x in details if is_same_position(x, model, keys)), None)

    if target:
        for k, v in model.items():
            if k not in target:
                target[k] = v
        if context.is_debug:
            target[DATASOUCE].extend(model[DATASOUCE])
    else:
        details.append(model)


def process_data(context: ProcessContext, data: Dict):
    if isinstance(data, Dict):
        table: TableProxy = get_table_schema(
            context, context.current_model[TABLE_NAME])
        for k, v in data:
            val = handle_value(context, v)
            if table is not None and table.get_column(k) is not None and isinstance(val, str):
                if table.is_number(k):
                    val = convert_str_to_decimal(val)
                elif table.is_oracle_date(k):
                    val = convert_str_to_date(val)
            context.current_model[k] = val


def create_model(table: str):
    return CaseDict({TABLE_NAME: table})


def process_product(context: ProcessContext, vpd: ValuationReportData):
    config = context.config
    if config.product is None:
        return

    pro = config.product
    logger.debug(f"开始处理指标表:{pro.table}")

    context.current_model = create_model(pro.table)
    process_data(context, pro.values)
    vpd.product = context.current_model


def handle_value(context: ProcessContext, define: DataCell | str | int | float):
    if isinstance(define, str):
        if define in context.env:
            return context.env.get(define)
        return define

    if isinstance(define, int) or isinstance(define, float):
        return define

    if define.formula is not None:
        return custom_eval(define.formula, context.current_model)

    return capture_data(context, define, context.current_row)


def process_excel_file_data(sheet: Sheet, config: ExcelConfig, env: dict) -> ValuationReportData:
    context = ProcessContext(sheet, config)
    context.env.update(env)
    context.is_debug = env.get(ENV_DEBUG, False)

    for i in range(len(sheet)):
        code = sheet.cell_value(i, context.subject_column)
        if code == '' or code == None:
            continue
        context.subject_row_map[code] = i

    vpd = ValuationReportData()
    process_positions(context, vpd)
    process_product(context, vpd)

    return vpd
