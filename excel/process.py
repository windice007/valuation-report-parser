
import re
import pyexcel as p
from typing import List
from excel.define import DataCell, ExcelConfig, PositionDefine, ValueDefine
from pyexcel.sheet import Sheet
from base.utils import excel_column_index, is_position_column_str, is_position_str
import model.mysql_models as MODEL
from base.logger import logger
from sqlalchemy.orm.attributes import InstrumentedAttribute
from decimal import Decimal


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


class ValuationReportData:
    def __init__(self) -> None:
        self.details = {}
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


def set_value(obj: object, vd: ValueDefine, v: any):
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
    return eval(formula, None, local)


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
                            t_code = f"{big_code}_{cls_code}_{t_code}"

                        if pos_type == "INDICBASEPORTPOSDTL":
                            big_code = getattr(obj, "AST_BIG_CLS_CODE")
                            cls_code = getattr(obj, "INVES_CLS_CODE")
                            t_code = f"{big_code}_{cls_code}_{t_code}"

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

    for k, v in config.positions.items():
        logger.debug(f"处理持仓：{k}")
        process_position(context, k, v, vpd)


def process_product(context: ProcessContext, vpd: ValuationReportData):
    pro = context.config.product
    Model = getattr(MODEL, pro.model)

    logger.debug(f"开始处理指标表:{pro.model}")

    m = Model()
    for v in pro.values:
        logger.debug(f"处理指标表字段:{v.column}")
        if v.cell:
            set_value(m, v, capture_data(context, v.cell))
        elif v.formula:
            d = custom_eval(v.formula, m.__dict__)
            set_value(m, v, d)
        else:
            set_value(m, v, v.value)
    vpd.product = m


def process_excel_file_data(file, config: ExcelConfig) -> ValuationReportData:
    sheet = p.get_sheet(file_name=file)
    context = ProcessContext(sheet, config)
    context.env["$FILE_NAME"] = file

    for i in range(len(sheet)):
        code = sheet.cell_value(i, context.subject_column)
        if code == '' or code == None:
            continue
        context.subject_row_map[code] = i

    vpd = ValuationReportData()
    process_positions(context, vpd)
    process_product(context, vpd)

    return vpd
