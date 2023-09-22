from datetime import datetime, date
import re
from vrp import Args, __version__
from vrp.base import (
    DATASOUCE,
    ENV_FILE_NAME,
    ENV_PROCESS_TIME,
    ENV_APP_VERSION,
    ENV_ROW_INDEX,
    ENV_PREFIX,
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
from sqlalchemy import Table, Numeric, String, Date, DateTime
from dateutil.parser import parse as parse_date
import pyexcel
import os


class ProcessContext:
    def __init__(self, sheet: Sheet, config: ExcelConfig) -> None:
        self.sheet = sheet
        self.config = config
        self.subject_column = excel_column_index(config.subject_code_column)
        self.spare_subject_column = (
            excel_column_index(config.spare_subject_code_column)
            if is_position_column_str(config.spare_subject_code_column)
            else None
        )
        self.env: dict[str] = None
        self.sink: MultiSink = None
        self.current_row = None
        self.current_row_code = None
        self.current_model = None
        self.current_column = None
        self.current_table = None
        self.is_debug: bool = False
        self.subject_row_map: dict = {}

    def reset(self):
        self.current_row = None
        self.current_row_code = None
        self.current_model = None
        self.current_column = None
        self.current_table = None

    def is_oracle(self) -> bool:
        db_sink: DbSink = self.sink.db_sink
        return db_sink.db_type == "oracle"


def capture_data(context: ProcessContext, cell: DataCell, row: int = None) -> str:
    sheet = context.sheet
    if cell is None:
        return None
    cell_value = cell.value
    if cell_value in context.env:
        cell_value = context.env.get(cell_value)

    if cell.address is not None and cell_value is None:
        if is_position_str(cell.address):
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
                    logger.warn(
                        f"DataCell.subject_code 配置不正确，未找到指定的科目：'{context.current_column}'->'{subject_code}'"
                    )
            else:
                if row is None:
                    logger.error(
                        f"DataCell.address 配置不正确，相对地址不可用：'{context.current_column}'->'{cell.address}'"
                    )
                else:
                    cell_value = sheet.cell_value(row, column_index)
        else:
            logger.error(
                f"DataCell.address 配置不正确，不是正确的格式：'{context.current_column}'->'{cell.address}'"
            )

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
            logger.warn(
                f"DataCell.capture_regex 配置不正确，未捕获到数据：'{context.current_column}'->'{cell.capture_regex}'->'{cell_value}'"
            )
            cell_value = None

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


def convert_str_to_date(v: str) -> date:
    dt = convert_str_to_datetime(v)
    return dt.date() if dt is not None else None


def convert_str_to_datetime(v: str) -> datetime:
    if v == "":
        return None
    return parse_date(v)


def convert_any_to_str(v) -> str:
    if v is None:
        return None
    return str(v)


FORMULA_ENV_PREFIX: str = "__ENV__"
FORMULA_VALUE = FORMULA_ENV_PREFIX + "VALUE"


def convert_env(m):
    return FORMULA_ENV_PREFIX + m[1]


def formula_eval(context: ProcessContext, formula: str, params: dict):
    local = context.current_model
    globs = {"Decimal": safe_float}

    if isinstance(params, dict):
        globs.update(params)
    if ENV_PREFIX in formula:
        for k, v in context.env.items():
            globs[k.replace(ENV_PREFIX, FORMULA_ENV_PREFIX)] = v
        formula = re.sub(f"\{ENV_PREFIX}(\w+)", convert_env, formula)

    try:
        return eval(formula, globs, local)
    except NameError as err:
        logger.error(
            f"公式计算发生错误：变量'{err.name.replace(FORMULA_ENV_PREFIX,ENV_PREFIX)}'未找到。"
        )


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
    context.current_table = pos.table
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
            start_row = (
                handler.start_row - 1 if isinstance(handler.start_row, int) else 0
            )
            for i in range(len(sheet)):
                if i < start_row:
                    continue
                code = sheet.cell_value(i, context.subject_column)
                if code == "" or code == None:
                    continue
                if re.search(handler.subject_filter_regex, str(code)):
                    context.current_model = create_model(pos.table)
                    if context.is_debug:
                        context.current_model[DATASOUCE] = [code]
                    context.current_row = i
                    context.current_row_code = code
                    context.env[ENV_ROW_INDEX] = i
                    process_data(context, pos.default)
                    process_data(context, group.default)
                    process_data(context, handler.values)

                    commit = True
                    if isinstance(handler.post_filter_formula, str):
                        commit = bool(
                            formula_eval(context, handler.post_filter_formula, None)
                        )
                    if commit:
                        if handler_index == 0:
                            details.append(context.current_model)
                        else:
                            merge_details(
                                context, details, context.current_model, handler
                            )
                    else:
                        logger.debug(
                            f"Handler:{handler.subject_filter_regex} Code:{code} Ignored by {handler.post_filter_formula}"
                        )
                    handle_count = handle_count + 1
            if handle_count > 0:
                logger.info(
                    f"Handler:'{handler.subject_filter_regex}'  Count:{handle_count}"
                )
            else:
                logger.warn(
                    f"Handler:'{handler.subject_filter_regex}'  Count:{handle_count}"
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

    def is_str(self, name: str):
        column = self.get_column(name)
        return isinstance(column.type, String)

    def is_date(self, name: str):
        column = self.get_column(name)
        return isinstance(column.type, Date)

    def is_datetime(self, name: str):
        column = self.get_column(name)
        return isinstance(column.type, DateTime)


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
        table: TableProxy = (
            get_table_schema(context, context.current_model[TABLE_NAME])
            if context.current_model
            else None
        )
        for k, v in data:
            logger.debug(f"数据处理：{k}, {v}")
            context.current_column = k
            val = handle_value(context, v)
            if table is not None and table.get_column(k) is not None:
                if isinstance(val, str):
                    if table.is_number(k):
                        val = convert_str_to_decimal(val)
                    elif table.is_date(k):
                        val = convert_str_to_date(val)
                    elif table.is_datetime(k):
                        val = convert_str_to_datetime(val)
                elif table.is_str(k):
                    val = convert_any_to_str(val)
            elif isinstance(v, Dict) and isinstance(v.type, str):
                cell: DataCell = v
                if isinstance(val, str):
                    if cell.type == "number":
                        val = convert_str_to_decimal(val)
                    elif cell.type == "date":
                        val = convert_str_to_date(val)
                    elif cell.type == "datetime":
                        val = convert_str_to_datetime(val)
                elif cell.type == "str":
                    val = convert_any_to_str(val)

            if context.current_model:
                context.current_model[k] = val
            else:
                context.env[f"{ENV_PREFIX}{k}"] = val


def create_model(table: str):
    return CaseDict({TABLE_NAME: table})


def process_products(context: ProcessContext, vpd: ValuationReportData):
    config = context.config
    if not isinstance(config.products, list):
        logger.warn(f"配置文件没有产品定义，不会生成产品数据")
        return

    for pro in config.products:
        logger.debug(f"开始处理指标表:{pro.table}")
        context.current_table = pro.table
        context.current_model = create_model(pro.table)
        process_data(context, pro.values)
        vpd.products.append(context.current_model)


def process_env(context: ProcessContext):
    config = context.config
    if config.env is None:
        return

    logger.debug("开始处理环境变量")
    process_data(context, config.env)


def is_valid_mapping_key(k: str):
    return k != "" and k != DEFAULT_KEY


DEFAULT_KEY: str = ENV_PREFIX + "_"


def handle_mapping(context: ProcessContext, cell: DataCell, cell_value: str):
    if isinstance(cell.mapping, Dict):
        if cell.mapping_rule == "contains":
            for k, v in cell.mapping:
                if is_valid_mapping_key(k) and k in cell_value:
                    return v
        if cell.mapping_rule == "regex":
            for k, v in cell.mapping:
                if is_valid_mapping_key(k) and re.search(k, cell_value):
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
        logger.warn(f"Decimal转换失败：{v}")
        return Decimal(0)


def handle_value(context: ProcessContext, define: DataCell | str | int | float | list):
    if define is None:
        return None

    if isinstance(define, list):
        cv = None
        for item in define:
            need_process = True

            if isinstance(item, Dict):
                cell: DataCell = item

                if cell.filter_formula is not None and not formula_eval(
                    context, cell.filter_formula, {FORMULA_VALUE: cv}
                ):
                    need_process = False

                if cell.subject_filter_regex is not None and not re.search(
                    cell.subject_filter_regex, str(context.current_row_code)
                ):
                    need_process = False

            if need_process:
                cv = handle_value(context, item)
        return cv

    if isinstance(define, str):
        if define in context.env:
            return context.env.get(define)
        return define

    if isinstance(define, int) or isinstance(define, float):
        return define

    cell_value = capture_data(context, define, context.current_row)

    if define.formula is not None:
        cell_value = formula_eval(context, define.formula, {FORMULA_VALUE: cell_value})

    logger.debug(f"数据处理结果(mapping前)：{cell_value}")

    return handle_mapping(context, define, cell_value)


def process(files: list[str], config: ExcelConfig, args: Args, sink: MultiSink):
    if config is None:
        logger.error(f"未找到估值表解析配置：{args.config}")
        exit(1)
    for file in files:
        process_excel_file(file, config, args, sink)


def process_excel_file(file: str, config: ExcelConfig, args: Args, sink: MultiSink):
    logger.info(f"开始处理估值文件：{file}")
    sheet = pyexcel.get_sheet(file_name=file, sheet_name=config.sheet_name)

    context = ProcessContext(sheet, config)
    context.is_debug = args.debug
    context.sink = sink
    context.env = {
        ENV_FILE_NAME: os.path.basename(file),
        ENV_PROCESS_TIME: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ENV_APP_VERSION: __version__,
        ENV_ROW_INDEX: None,
    }

    for i in range(len(sheet)):
        code = sheet.cell_value(i, context.subject_column)
        if code == "" or code is None:
            if context.spare_subject_column is not None:
                code = sheet.cell_value(i, context.spare_subject_column)
                if code == "" or code is None:
                    continue
            else:
                continue
        context.subject_row_map[code] = i
        context.subject_row_map[str(code)] = i

    process_env(context)
    context.reset()
    vpd = ValuationReportData(file)
    process_positions(context, vpd)
    context.env[ENV_ROW_INDEX] = None
    context.reset()
    process_products(context, vpd)

    logger.info(f"估值文件处理完成，持仓记录{len(vpd.details)}条，产品记录{len(vpd.products)}条。")
    sink.save(vpd)
