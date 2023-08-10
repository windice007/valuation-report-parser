from datetime import datetime
import re
from vrp import Args
from vrp.base import (
    DATASOUCE,
    ENV_FILE_NAME,
    ENV_PROCESS_TIME,
    TABLE_NAME,
    CaseDict,
    ValuationReportData,
)
from vrp.excel.define import DataCell, ExcelConfig, HandlerDefine, PositionDefine
from pyexcel.sheet import Sheet
from vrp.base.utils import excel_column_index, is_position_column_str, is_position_str
from vrp.excel.sink import DbSink, MultiSink
from vrp.excel.utils import Dict
from vrp.base.logger import logger
from decimal import Decimal
from sqlalchemy import Table, Numeric
from dateutil.parser import parse as parse_date
import pyexcel


class ProcessContext:
    def __init__(self, sheet: Sheet, config: ExcelConfig) -> None:
        self.sheet = sheet
        self.config = config
        self.subject_column = excel_column_index(config.subject_code_column)
        self.env: dict = None
        self.sink: MultiSink = None
        self.current_row = -1
        self.current_model = {}
        self.is_debug: bool = False
        self.subject_row_map: dict = {}

    def is_oracle(self) -> bool:
        db_sink: DbSink = self.sink.db_sink
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
        match = re.search(re.compile(cell.capture_regex), str(cell_value))
        if match:
            if len(match.groups()) > 0:
                cell_value = match[1]
            else:
                cell_value = match[0]
        else:
            logger.warn(f"未捕获到指定字段：[{cell_value}]@[{cell.capture_regex}]")
            cell_value = None

    if cell.type == "number" and isinstance(cell_value, str):
        cell_value = convert_str_to_decimal(cell_value)
    elif cell.type == "str" and not isinstance(cell_value, str):
        cell_value = str(cell_value)
    return cell_value


def get_cell_subject_code(
    context: ProcessContext, cell: DataCell, row: int = None
) -> str:
    if isinstance(cell.subject_code, Dict):
        return capture_data(context, cell.subject_code, row)
    return cell.subject_code


def convert_str_to_decimal(v: str) -> Decimal:
    v = v.replace(",", "")
    if v == "":
        return Decimal(0)
    elif v.endswith("%"):
        return Decimal(v.rstrip("%")) / 100
    else:
        return Decimal(v)


def convert_str_to_date(v: str) -> datetime:
    return parse_date(v)


def custom_eval(formula: str, globals: dict, local: dict):
    if isinstance(local, dict):
        return eval(formula, globals, local)
    return eval(formula, globals, local.__dict__)


def process_positions(context: ProcessContext, vpd: ValuationReportData):
    config = context.config

    if config.positions is None:
        logger.warn(f"配置文件没有持仓定义，不会生成持仓数据")
        return

    for pos in config.positions:
        logger.debug(f"处理持仓：{pos}")
        handle_position(context, pos, vpd)


def handle_position(
    context: ProcessContext, pos: PositionDefine, vpd: ValuationReportData
):
    sheet = context.sheet
    if not isinstance(pos.groups, list):
        logger.warn(f"没有有效的持仓定义:{pos.table}")
        return

    for group in pos.groups:
        details = []
        if not isinstance(group.handlers, list):
            logger.warn(f"没有有效的处理配置:{pos.table}")
            continue
        handler_index = 0
        for handler in group.handlers:
            logger.debug(f"Handler:{handler.subject_filter_regex}")
            handle_count = 0
            for i in range(len(sheet)):
                code = sheet.cell_value(i, context.subject_column)
                if code == "" or code == None:
                    continue
                if re.search(handler.subject_filter_regex, str(code)):
                    context.current_model = create_model(pos.table)
                    if context.is_debug:
                        context.current_model[DATASOUCE] = [code]
                    context.current_row = i
                    process_data(context, pos.default)
                    process_data(context, group.default)
                    process_data(context, handler.values)
                    if handler_index == 0:
                        details.append(context.current_model)
                    else:
                        merge_details(context, details, context.current_model, handler)
                    handle_count = handle_count + 1
            if handle_count > 0:
                logger.info(
                    f"Handler:{handler.subject_filter_regex}  Count:{handle_count}"
                )
            else:
                logger.warn(
                    f"Handler:{handler.subject_filter_regex}  Count:{handle_count}"
                )

            handler_index = handler_index + 1
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
        return self.table.primary_key.columns.keys()

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
    db_sink: DbSink = context.sink.db_sink
    return TableProxy(db_sink.get_table(table_name)) if db_sink is not None else None


def merge_details(
    context: ProcessContext, details: list, model: Dict, handler: HandlerDefine
):
    keys = handler.merge_keys
    if keys is None or len(keys) == 0:
        table: TableProxy = get_table_schema(context, model[TABLE_NAME])

        if table is None:
            details.append(model)
            return

        keys = table.keys()
    target: dict = next((x for x in details if is_same_position(x, model, keys)), None)

    if target:
        for k, _ in handler.values:
            target[k] = model[k]
        if context.is_debug:
            target[DATASOUCE].extend(model[DATASOUCE])


def process_data(context: ProcessContext, data: Dict):
    if isinstance(data, Dict):
        table: TableProxy = get_table_schema(context, context.current_model[TABLE_NAME])
        for k, v in data:
            logger.debug(f"数据处理：{k}, {v}")
            val = handle_value(context, v)
            if (
                table is not None
                and table.get_column(k) is not None
                and isinstance(val, str)
            ):
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
        logger.warn(f"配置文件没有产品定义，不会生成产品数据")
        return

    pro = config.product
    logger.debug(f"开始处理指标表:{pro.table}")

    context.current_model = create_model(pro.table)
    process_data(context, pro.values)
    vpd.product = context.current_model


def is_valid_mapping_key(k: str):
    return k != "" and k != DEFAULT_KEY


DEFAULT_KEY: str = "$_"


def handle_mapping(context: ProcessContext, cell: DataCell, cell_value: str):
    if isinstance(cell.mapping, Dict):
        if cell.mapping_rule == "contains":
            for k, v in cell.mapping:
                if is_valid_mapping_key(k) and k in cell_value:
                    return v
        if cell.mapping_rule == "regex":
            for k, v in cell.mapping:
                if is_valid_mapping_key(k) and re.match(k, cell_value):
                    return v
        if cell_value in cell.mapping:
            cell_value = getattr(cell.mapping, cell_value)
        elif DEFAULT_KEY in cell.mapping:
            cell_value = getattr(cell.mapping, DEFAULT_KEY)
    return cell_value


def safe_float(v):
    try:
        return Decimal(v)
    except:
        return Decimal(0)


def handle_value(context: ProcessContext, define: DataCell | str | int | float):
    if define is None:
        return None

    if isinstance(define, str):
        if define in context.env:
            return context.env.get(define)
        return define

    if isinstance(define, int) or isinstance(define, float):
        return define

    cell_value = capture_data(context, define, context.current_row)

    if define.formula is not None:
        globals = {"VALUE": cell_value, "Decimal": safe_float}
        globals.update(context.env)
        cell_value = custom_eval(define.formula, globals, context.current_model)

    logger.debug(f"数据处理结果(mapping前)：{cell_value}")

    return handle_mapping(context, define, cell_value)


def process(files: list[str], config: ExcelConfig, args: Args, sink: MultiSink):
    for file in files:
        process_excel_file(file, config, args, sink)


def process_excel_file(file: str, config: ExcelConfig, args: Args, sink: MultiSink):
    logger.info(f"开始处理估值文件：{file}")
    sheet = pyexcel.get_sheet(file_name=file, sheet_name=config.sheet_name)

    context = ProcessContext(sheet, config)
    context.is_debug = args.debug
    context.sink = sink
    context.env = {
        ENV_FILE_NAME: file,
        ENV_PROCESS_TIME: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    for i in range(len(sheet)):
        code = sheet.cell_value(i, context.subject_column)
        if code == "" or code == None:
            continue
        context.subject_row_map[code] = i
        context.subject_row_map[str(code)] = i

    vpd = ValuationReportData(file)
    process_positions(context, vpd)
    process_product(context, vpd)

    logger.info(
        f"估值文件处理完成，持仓记录{len(vpd.details)}条，产品记录{0 if vpd.product is None else 1}条。"
    )
    sink.save(vpd)
