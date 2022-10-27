
import re
import pyexcel as p
from typing import List
from excel.define import DataCell, ExcelConfig, PositionDefine, ValueDefine
from pyexcel.sheet import Sheet
from base.utils import excel_column_index, is_position_str
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


class ValuationReportData:
    def __init__(self) -> None:
        self.details = {}
        self.product = None


def capture_data(context: ProcessContext, cell: DataCell, row: int = None) -> str:
    sheet = context.sheet
    if cell == None or cell.address == None:
        return None
    cell_value = None
    if is_position_str(cell.address):
        cell_value = sheet[cell.address]
    else:
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

    if cell_value is None:
        return None

    if cell.capture_regex != None:
        match = re.search(re.compile(cell.capture_regex), cell_value)
        if match:
            groups = match.groups()
            if len(groups) > 0:
                cell_value = match[1]
            else:
                cell_value = match[0]

    if isinstance(cell.mapping, dict) and cell_value in cell.mapping:
        cell_value = cell.mapping.get(cell_value)
    return cell_value


def get_cell_subject_code(context: ProcessContext, cell: DataCell, row: int = None) -> str:
    if isinstance(cell.subject_code, DataCell):
        return capture_data(context, cell.subject_code, row)
    return cell.subject_code


def convert_str_to_decimal(v: str) -> Decimal:
    if v == '':
        return Decimal(0)
    elif v.endswith("%"):
        return Decimal(v.rstrip("%"))/100
    else:
        return Decimal(v)


def set_value(obj: object, vd: ValueDefine, v: any):
    if isinstance(vd.mapping, dict) and v in vd.mapping:
        v = vd.mapping.get(v)

    if hasattr(type(obj), vd.column):
        c_define: InstrumentedAttribute = getattr(type(obj), vd.column)
        if c_define:
            t = c_define.expression.type.python_type

            if t is Decimal and isinstance(v, str):
                v = convert_str_to_decimal(v)

    setattr(obj, vd.column, v)


def custom_eval(formula: str, local: dict):
    return eval(formula, None, local)


def process_position(context: ProcessContext,  pos_type: str, defines: List[PositionDefine], vpd: ValuationReportData):
    if not isinstance(defines, list):
        return
    sheet = context.sheet
    config = context.config
    Model = getattr(MODEL, pos_type)

    for pd in defines:
        for sd in pd.subjects:
            for i in range(len(sheet)):
                code = sheet.cell_value(i, context.subject_column)
                if code == '' or code == None:
                    continue
                match = re.search(re.compile(
                    config.subject_code_detail_regex), code)
                if match:
                    s_code = match[1]
                    if re.search(sd.code, s_code):
                        t_code = match[2]

                        if t_code not in vpd.details:
                            obj = Model()
                            vpd.details[t_code] = obj
                            if pd.default:
                                for k, v in pd.default.items():
                                    if isinstance(v, DataCell):
                                        setattr(
                                            obj, k, capture_data(context, v))
                                    else:
                                        setattr(obj, k, v)

                        obj = vpd.details[t_code]

                        for vd in sd.values:
                            d = None
                            if vd.cell:
                                d = capture_data(context, vd.cell, i)
                            else:
                                d = custom_eval(vd.formula, obj.__dict__)

                            if d is None:
                                continue

                            v = getattr(obj, vd.column)
                            if v is None:
                                set_value(obj, vd, d)
                            else:
                                set_value(obj, vd, d+v)


def process_positions(context: ProcessContext, vpd: ValuationReportData):
    config = context.config

    for k, v in config.positions.items():
        process_position(context, k, v, vpd)


def process_product(context: ProcessContext, vpd: ValuationReportData):
    pro = context.config.product
    Model = getattr(MODEL, pro.model)

    m = Model()
    for v in pro.values:
        if v.cell:
            set_value(m, v, capture_data(context, v.cell))
        else:
            d = custom_eval(v.formula, m.__dict__)
            set_value(m, v, d)
    vpd.product = m


def process_excel_file_data(file, config: ExcelConfig) -> ValuationReportData:
    sheet = p.get_sheet(file_name=file)
    context = ProcessContext(sheet, config)

    for i in range(len(sheet)):
        code = sheet.cell_value(i, context.subject_column)
        if code == '' or code == None:
            continue
        context.subject_row_map[code] = i

    vpd = ValuationReportData()
    process_positions(context, vpd)
    process_product(context, vpd)

    return vpd
