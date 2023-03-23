
import re
import pyexcel as p
from typing import List
from excel.define import DataCell, ExcelConfig, PositionDefine
from pyexcel.sheet import Sheet
from base.utils import excel_column_index, is_position_column_str, is_position_str
from excel.utils import Dict
import model.mysql_models as MODEL
from base.logger import logger
from sqlalchemy.orm.attributes import InstrumentedAttribute
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
        if match and len(match.groups()) > 0:
            cell_value = match[1]
        else:
            logger.warn(f"未捕获到指定字段：[{cell_value}]@[{cell.capture_regex}]")
            cell_value = None

    if isinstance(cell.mapping, dict) and cell_value in cell.mapping:
        cell_value = cell.mapping.get(cell_value)
    return cell_value


def get_cell_subject_code(context: ProcessContext, cell: DataCell, row: int = None) -> str:
    if isinstance(cell.subject_code, DataCell):
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


def set_value(obj: object, vd, v: any):
    if isinstance(vd.mapping, dict) and v in vd.mapping:
        v = vd.mapping.get(v)
    set_column_value(obj, vd.column, v)


def set_column_value(obj: object, column: str, v: any):
    if hasattr(type(obj), column):
        c_define: InstrumentedAttribute = getattr(type(obj), column)
        if c_define:
            t = c_define.expression.type.python_type

            if t is Decimal and isinstance(v, str):
                v = convert_str_to_decimal(v)

    setattr(obj, column, v)


def custom_eval(formula: str, local: dict):
    if isinstance(local, dict):
        return eval(formula, None, local)
    return eval(formula, None, local.__dict__)


def process_position(context: ProcessContext,  pos_type: str, defines: List[PositionDefine], vpd: ValuationReportData):
    if not isinstance(defines, list):
        return
    sheet = context.sheet
    config = context.config
    Model = getattr(MODEL, pos_type)

    for pd in defines:
        subject_code_detail_regex = config.subject_code_detail_regex
        if isinstance(pd.subject_code_detail_regex, str):
            subject_code_detail_regex = pd.subject_code_detail_regex
        for sd in pd.subjects:
            logger.debug(f"处理持仓科目定义，匹配：{sd.code}")
            repeat_checker = {}
            for i in range(len(sheet)):
                code = sheet.cell_value(i, context.subject_column)
                if code == '' or code == None:
                    continue
                match = None
                if sd.direct_match:
                    match = [code, code, code]
                else:
                    match = re.search(re.compile(
                        subject_code_detail_regex), code)
                if match:
                    s_code = match[1]
                    if re.search(sd.code, s_code):
                        logger.debug(f"处理持仓：{code}")
                        t_code = match[2]

                        # 生成对象
                        obj = Model()
                        setattr(obj, "_id", t_code)
                        setattr(obj, "_code", code)
                        if pd.default:
                            for k, v in pd.default.items():
                                logger.debug(f"处理持仓字段默认值：{k}")
                                if isinstance(v, DataCell):
                                    set_column_value(
                                        obj, k, capture_data(context, v, i))
                                elif v in context.env:
                                    set_column_value(
                                        obj, k, context.env.get(v))
                                else:
                                    set_column_value(obj, k, v)

                        for vd in sd.values:
                            logger.debug(f"处理持仓字段值：{vd.column}")
                            d = None
                            if vd.cell:
                                d = capture_data(context, vd.cell, i)
                            elif vd.formula:
                                d = custom_eval(vd.formula, obj.__dict__)
                            else:
                                d = vd.value

                            if d is None or d == '':
                                logger.debug(f"持仓字段值为空：{vd.column}，跳过赋值。")
                                continue

                            v = getattr(obj, vd.column)
                            if v is None:
                                set_value(obj, vd, d)
                            else:
                                set_value(obj, vd, d+v)
                            # 生成结束

                        # 资产大类特殊处理
                        if pos_type == "VALUATIONPORTPOSDTL":
                            big_code = getattr(obj, "AST_CLS_CODE")
                            cls_code = getattr(obj, "INV_CLS_CODE")
                            attr_code = getattr(obj, "HOLD_ATTR_CODE")
                            t_code = f"{big_code}_{cls_code}_{attr_code}_{t_code}"

                        setattr(obj, "_id", t_code)

                        if t_code in repeat_checker:
                            logger.warn(f"同一处理科目下出现了重复匹配:[{t_code}@{sd.code}]")
                        else:
                            repeat_checker[t_code] = obj

                        if t_code not in vpd.details:
                            vpd.details[t_code] = obj
                        else:
                            merge_object(vpd.details[t_code], obj)


def merge_object(obj1, obj2):
    for att in dir(obj2):
        oldv = getattr(obj1, att)
        if oldv is None:
            setattr(obj1, att, getattr(obj2, att))


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
                    context.current_row = i
                    process_data(context, pos.default)
                    process_data(context, group.default)
                    process_data(context, handler.values)
                    vpd.details.append(context.current_model)

def refactor_position(vpd:ValuationReportData):
    pass    


def process_data(context: ProcessContext, data: Dict):
    if isinstance(data, Dict):
        for k, v in data:
            if isinstance(context.current_model, dict):
                context.current_model[k] = handle_value(context, v)
            else:
                set_column_value(context.current_model, k,
                                 handle_value(context, v))


def create_model(table: str):
    properties = vars(MODEL)
    for v in properties.values():
        if isinstance(v, type) and issubclass(v, MODEL.Base) and v is not MODEL.Base:
            t = getattr(v, "__tablename__")
            if t == table:
                return v()
    return {"__tablename__": table}


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
