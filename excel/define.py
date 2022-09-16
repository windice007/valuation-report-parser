import re
from typing import List
import pyexcel as p
from pyexcel.sheet import Sheet
from base.utils import excel_column_index


class ProcessContext:
    sheet: Sheet | None = None
    row: int | None = None
    subject_column: int = None

    def __init__(self, sheet: Sheet) -> None:
        self.sheet = sheet


class DataCell:
    address: str | int | None = None
    capture_regex = None

    def __init__(self, address, regex=None):
        self.address = address
        self.capture_regex = regex


class ValueDefine:
    column: str = None
    cell: DataCell = None


class SubjectDefine:
    code: str = None
    values: List[ValueDefine] = None


class PositionDefine:
    subjects: List[SubjectDefine] = None


class ExcelConfig:
    start_row = 4
    valuation_date: DataCell | None = None
    product_code: DataCell | None = None
    subject_code_column = "B"
    subject_code_detail_regex = r"^\d{8}(.+)$"
    pos_bond_define: list = None
    pos_stock_define: list = None


class ValuationReportData:
    productCode: str | None = None
    productName: str | None = None
    valuationDate: str | None = None
    details = []
    summaries = []


def capture_data(context: ProcessContext, cell: DataCell) -> str:
    if cell == None or cell.address == None:
        return None
    sheet = context.sheet
    cell_value = sheet[cell.address]

    if cell.capture_regex != None:
        match = re.search(re.compile(cell.capture_regex), cell_value)
        if match:
            groups = match.groups()
            if len(groups) > 0:
                return match[1]
            return match[0]
    return cell_value


def process_excel_stream_data(stream, extension, config: ExcelConfig) -> Sheet:
    return p.get_sheet(file_stream=stream, file_type=extension)


def process_excel_file_data(file, config: ExcelConfig) -> ValuationReportData:
    sheet = p.get_sheet(
        file_name=file)

    context = ProcessContext(sheet)
    context.subject_column = excel_column_index(config.subject_code_column)

    vpd = ValuationReportData()
    vpd.productCode = capture_data(context, config.product_code)
    vpd.valuationDate = capture_data(context, config.valuation_date)

    for i in range(len(sheet)):
        code = sheet.cell_value(i, context.subject_column)
        if code == '' or code == None:
            continue
        match = re.search(re.compile(config.subject_code_detail_regex), code)
        if match:
            s_code = match[1]
            print(s_code)

    return vpd
