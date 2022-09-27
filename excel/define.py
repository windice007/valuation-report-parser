from turtle import position
from typing import List


class DataCell:
    address: str | None = None
    capture_regex: str | None = None

    def __init__(self, address=None, regex=None):
        self.address = address
        self.capture_regex = regex


class ValueDefine:
    subject_code: str = None
    column: str = None
    cell: DataCell = None

    def __init__(self) -> None:
        self.subject_code = None
        self.column = None
        self.cell = None


class SubjectDefine:
    code: str = None
    values: List[ValueDefine] = None

    def __init__(self) -> None:
        self.code = None
        self.values = []


class PositionDefine:
    default: dict | None = None
    subjects: List[SubjectDefine] = None

    def __init__(self) -> None:
        self.default = {}
        self.subjects = []


class ProductDefine:
    def __init__(self) -> None:
        self.model = None
        self.values: List[ValueDefine] = []


class ExcelConfig:
    def __init__(self) -> None:
        self.start_row = 4
        self.global_data = {}
        self.subject_code_column = "B"
        self.subject_code_detail_regex = r"^(\d{8})(.+)$"
        self.positions = {}
        self.product: ProductDefine | None = None
