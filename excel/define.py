from typing import List


class DataCell:
    def __init__(self, address=None, regex=None):
        self.address: str = address
        self.capture_regex: str = regex
        self.subject_code: str = None
        self.mapping: dict = None


class ValueDefine:
    def __init__(self) -> None:
        self.column: str = None
        self.cell: DataCell = None
        self.formula: str = None
        self.mapping: dict = None
        self.value: any = None


class SubjectDefine:
    def __init__(self) -> None:
        self.code: str | None = None
        self.direct_match = False
        self.values: List[ValueDefine] = []


class PositionDefine:
    def __init__(self) -> None:
        self.subject_code_detail_regex: str | None = None
        self.default: dict | None = {}
        self.subjects: List[SubjectDefine] = []


class ProductDefine:
    def __init__(self) -> None:
        self.model = None
        self.values: List[ValueDefine] = []


class ExcelConfig:
    def __init__(self) -> None:
        self.start_row = 4
        self.subject_code_column = "B"
        self.subject_code_detail_regex = r"^(\d{8})(.+)$"
        self.positions = {}
        self.product: ProductDefine | None = None
