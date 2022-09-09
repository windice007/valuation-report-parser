import pyexcel as p
from pyexcel.sheet import Sheet


class ExcelConfig:
    start_row = 4
    start_column = 1


class ValuationReportData:
    productCode = None
    productName = None
    valuationDate = None
    details = []
    summaries = []


def process_excel_stream_data(stream, extension, config: ExcelConfig) -> Sheet:
    return p.get_sheet(file_stream=stream, file_type=extension)


def process_excel_file_data(file, config: ExcelConfig = None) -> Sheet:
    return p.get_sheet(file_name=file)
