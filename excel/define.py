import re
import pyexcel as p
from pyexcel.sheet import Sheet


class ProcessContext:
    sheet: Sheet | None = None
    row: int | None = None

    def __init__(self, sheet: Sheet) -> None:
        self.sheet = sheet


class DataCell:
    address: str | int | None = None
    capture_regex = None

    def __init__(self, address, regex=None):
        self.address = address
        self.capture_regex = regex


class ExcelConfig:
    start_row = 4
    start_column = 1
    valuation_date: DataCell | None = None
    product_code: DataCell | None = None
    subject_code_index = 0
    subject_code_detail_regex = r"^\d{8}(\w+)$"


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

    vpd = ValuationReportData()
    vpd.productCode = capture_data(context, config.product_code)
    vpd.valuationDate = capture_data(context, config.valuation_date)

    return vpd
