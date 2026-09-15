from datetime import datetime, date
import re
from vrp import Args, __version__
from vrp.base import (
    DATASOUCE,
    ENV_COLUMN_COUNT,
    ENV_FILE_NAME,
    ENV_PROCESS_TIME,
    ENV_APP_VERSION,
    ENV_ROW_COUNT,
    ENV_ROW_INDEX,
    ENV_PREFIX,
    TABLE_NAME,
    CaseDict,
    ValuationReportData,
)
from vrp.excel.define import (
    DataCell,
    ExcelConfig,
    HandlerDefine,
    PositionDefine,
    Target_Type,
)
from pyexcel.sheet import Sheet
from vrp.base.utils import (
    excel_cell_position,
    excel_column_index,
    is_position_column_str,
    is_position_str,
)
from vrp.excel.sink import DbSink, MultiSink
from vrp.excel.utils import Dict
from vrp.base.logger import logger
from decimal import Decimal
from sqlalchemy import Table, Numeric, String, Date, DateTime
import os
from vrp.workbook.reader import read_sheet
from vrp.parsing.conversion import convert_any_to_str, convert_value
from vrp.parsing.dates import (
    convert_int_to_datetime,
    convert_str_to_date,
    convert_str_to_datetime,
)
from vrp.parsing.numbers import convert_str_to_decimal


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


def safe_cell_value(context: ProcessContext, row: int, column: int):
    sheet = context.sheet
    config = context.config
    try:
        return sheet.cell_value(row, column)
    except IndexError as err:
        if config.raise_index_out_range_error:
            raise err
        else:
            return None


def merged_value(context: ProcessContext, cell: DataCell, row: int, column: int):
    if row is None or column is None:
        return None

    if cell.merged_value == "auto":
        raise NotImplementedError("DataCell.merged_value : auto")
    else:
        match cell.merged_value:
            case "up":
                ro = -1
                co = 0
            case "down":
                ro = 1
                co = 0
            case "left":
                ro = 0
                co = -1
            case "right":
                ro = 0
                co = 1
        r = row
        c = column
        row_count = context.sheet.number_of_rows()
        column_count = context.sheet.number_of_columns()
        while True:
            r = r + ro
            c = c + co
            if not (0 <= r < row_count and 0 <= c < column_count):
                return None
            try:
                val = context.sheet.cell_value(r, c)
                if val is not None and val != "":
                    return val
            except:
                return None


def capture_data(context: ProcessContext, cell: DataCell, row: int = None) -> str:
    if cell is None:
        return None
    cell_value = cell.value
    if cell_value in context.env:
        cell_value = context.env.get(cell_value)

    if cell.address is not None and cell_value is None:
        if is_position_str(cell.address):
            r, c = excel_cell_position(cell.address)
            cell_value = safe_cell_value(context, r, c)
        elif is_position_column_str(cell.address):
            column_index = excel_column_index(cell.address)
            subject_code = get_cell_subject_code(context, cell, row)
            if isinstance(subject_code, str):
                if subject_code in context.subject_row_map:
                    r = context.subject_row_map[subject_code]
                    c = column_index
                    cell_value = safe_cell_value(context, r, c)
                else:
                    logger.warn(
                        f"DataCell.subject_code 配置不正确，未找到指定的科目：'{context.current_column}'->'{subject_code}'"
                    )
            else:
                if row is None:
                    logger.error(
                        f"DataCell.address 配置不正确，相对地址不可用：'{context.current_column}'->'{cell.address}'"
                    )
                else:
                    r = row
                    c = column_index
                    cell_value = safe_cell_value(context, row, column_index)
        else:
            logger.error(
                f"DataCell.address 配置不正确，不是正确的格式：'{context.current_column}'->'{cell.address}'"
            )

    if (cell_value is None or cell_value == "") and cell.merged_value is not None:
        temp = merged_value(context, cell, r, c)
        if temp is not None:
            cell_value = temp

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
                handler.start_row - 1 if isinstance(handler.start_row, int) else -1
            )
            for i in range(len(sheet)):
                if i < start_row:
                    continue
                if handler.stop_row is not None and i >= handler.stop_row:
                    break
                code = row_code_str(i, context)
                if code == "":
                    continue
                if re.search(handler.subject_filter_regex, code):
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

    def get_column_type(self, name: str) -> Target_Type | None:
        if self.is_number(name):
            return "number"
        if self.is_str(name):
            return "str"
        if self.is_date(name):
            return "date"
        if self.is_datetime(name):
            return "datetime"
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
            logger.debug(f"数据处理结果：{k}={val}，type={type(val)}")
            if table is not None and table.get_column(k) is not None:
                val = convert_value(
                    val, table.get_column_type(k), nullable=table.get_column(k).nullable
                )
            elif isinstance(v, Dict) and isinstance(v.type, str):
                cell: DataCell = v
                val = convert_value(val, cell.type)

            logger.debug(f"数据类型转换结果：{k}={val}，type={type(val)}")
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
        logger.debug(f"数据处理结果(mapping前)：{cell_value}")
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
        if isinstance(v, str):
            return convert_str_to_decimal(v)
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
        logger.debug(f"数据处理结果(公式前)：{cell_value}")
        cell_value = formula_eval(context, define.formula, {FORMULA_VALUE: cell_value})

    return handle_mapping(context, define, cell_value)


def process(files: list[str], config: ExcelConfig, args: Args, sink: MultiSink):
    if config is None:
        logger.error(f"未找到估值表解析配置：{args.config}")
        exit(1)
    for file in files:
        process_excel_file(file, config, args, sink)


def row_code_str(row: int, context: ProcessContext) -> str:
    sheet = context.sheet
    code = sheet.cell_value(row, context.subject_column)
    if code == "" or code is None:
        if context.spare_subject_column is not None:
            code = sheet.cell_value(row, context.spare_subject_column)
    return "" if code is None else str(code)


def process_excel_file(file: str, config: ExcelConfig, args: Args, sink: MultiSink):
    logger.info(f"开始处理估值文件：{file}")
    sheet = read_sheet(file, config.sheet_name)

    context = ProcessContext(sheet, config)
    context.is_debug = args.debug
    context.sink = sink
    context.env = {
        ENV_FILE_NAME: os.path.basename(file),
        ENV_PROCESS_TIME: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ENV_APP_VERSION: __version__,
        ENV_ROW_INDEX: None,
        ENV_ROW_COUNT: sheet.number_of_rows(),
        ENV_COLUMN_COUNT: sheet.number_of_columns(),
    }

    for i in range(len(sheet)):
        code = row_code_str(i, context)
        if code == "":
            continue
        context.subject_row_map[code] = i

    process_env(context)
    context.reset()
    vpd = ValuationReportData(file)
    process_positions(context, vpd)
    context.env[ENV_ROW_INDEX] = None
    context.reset()
    process_products(context, vpd)

    logger.info(
        f"估值文件处理完成，持仓记录{len(vpd.details)}条，产品记录{len(vpd.products)}条。"
    )
    sink.save(vpd)
