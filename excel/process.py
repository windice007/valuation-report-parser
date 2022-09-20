
import re
import pyexcel as p
from typing import List
from excel.define import DataCell, ExcelConfig, PositionDefine
from pyexcel.sheet import Sheet
from base.utils import excel_column_index
from model.mysql_models import BUSIPOSBOND


class ProcessContext:
    sheet: Sheet | None = None
    row: int | None = None
    subject_column: int | None = None
    config: ExcelConfig | None = None

    def __init__(self, sheet: Sheet, config: ExcelConfig) -> None:
        self.sheet = sheet
        self.config = config
        self.subject_column = excel_column_index(config.subject_code_column)


class ValuationReportData:
    productCode: str | None = None
    productName: str | None = None
    valuationDate: str | None = None
    details = []
    summaries = []


def capture_data(sheet: Sheet, cell: DataCell, row: int = None) -> str:
    if cell == None or cell.address == None:
        return None
    cell_value = None
    if row is None:
        cell_value = sheet[cell.address]
    else:
        column_index = excel_column_index(cell.address)
        cell_value = sheet.cell_value(row, column_index)

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


TYPE_MAPPING = {
    "pos_bond_define": BUSIPOSBOND
}


def process_position(context: ProcessContext,  pos_type: str):
    sheet = context.sheet
    config = context.config
    defines: List[PositionDefine] = getattr(config, pos_type)
    Model = TYPE_MAPPING[pos_type]
    data: dict = {}
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
                    if s_code == sd.code:
                        t_code = match[2]

                        if t_code not in data:
                            data[t_code] = Model()

                        obj = data[t_code]

                        for vd in sd.values:
                            d = capture_data(sheet, vd.cell, i)
                            setattr(obj, vd.column, d)
    return data


def process_positions(context: ProcessContext, vpd: ValuationReportData):
    d = process_position(context, "pos_bond_define")
    for x in d.values():
        vpd.details.append(x)


def process_excel_file_data(file, config: ExcelConfig) -> ValuationReportData:
    sheet = p.get_sheet(file_name=file)
    context = ProcessContext(sheet, config)

    vpd = ValuationReportData()
    vpd.productCode = capture_data(context.sheet, config.product_code)
    vpd.valuationDate = capture_data(context.sheet, config.valuation_date)

    process_positions(context, vpd)

    return vpd
