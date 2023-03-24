
import re
import pyexcel as p
from base.db_mysql import get_table_sink
from excel.define import DataCell, ExcelConfig, PositionDefine
from pyexcel.sheet import Sheet
from base.utils import excel_column_index, is_position_column_str, is_position_str
from excel.utils import Dict
from base.logger import logger
from decimal import Decimal
from datetime import datetime


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


class ValuationReportData:
    def __init__(self) -> None:
        self.details = []
        self.product = None


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
                    context.current_model[DATASOUCE] = [code]
                    context.current_row = i
                    process_data(context, pos.default)
                    process_data(context, group.default)
                    process_data(context, handler.values)
                    append_details(details, context.current_model)

    vpd.details.extend(details)


TABLE_NAME = "__tablename__"
DATASOUCE = "__datasource__"


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


def merge_dict(d1: dict, d2: dict):
    for k, v in d2.items():
        if k not in d1:
            d1[k] = v
    d1[DATASOUCE].extend(d2[DATASOUCE])


def get_db_sink(model: dict):
    table = model[TABLE_NAME]
    return get_table_sink(table)


def append_details(details: list, model: dict):
    sink = get_db_sink(model)
    pris = sink.primary_columns

    target = next(
        (x for x in details if is_same_position(x, model, pris)), None)

    if target:
        merge_dict(target, model)
    else:
        details.append(model)


def process_data(context: ProcessContext, data: Dict):
    if isinstance(data, Dict):
        sink = get_db_sink(context.current_model)
        for k, v in data:
            val = handle_value(context, v)
            if sink.has_column(k) and isinstance(val, str) and sink.is_decimal(k):
                val = convert_str_to_decimal(val)
            context.current_model[k] = val


def create_model(table: str):
    return {TABLE_NAME: table}


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


def process_excel_file_data(file, config: ExcelConfig) -> ValuationReportData:
    sheet = p.get_sheet(file_name=file)
    context = ProcessContext(sheet, config)
    context.env["$FILE_NAME"] = file
    context.env["$PROCESS_TIME"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for i in range(len(sheet)):
        code = sheet.cell_value(i, context.subject_column)
        if code == '' or code == None:
            continue
        context.subject_row_map[code] = i

    vpd = ValuationReportData()
    process_positions(context, vpd)
    process_product(context, vpd)

    return vpd
