from typing import List


class DataCell:
    address: str | None = None
    capture_regex: str | None = None

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
    subject_code_detail_regex = r"^(\d{8})(.+)$"
    pos_bond_define: List[PositionDefine] = None
    pos_stock_define: List[PositionDefine] = None
