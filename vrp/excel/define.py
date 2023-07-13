from typing import List, Literal


class DataCell:
    def __init__(self, address=None, regex=None):
        self.address: str = address
        self.capture_regex: str = regex
        self.subject_code: str = None
        self.mapping: dict = None
        self.formula: str = None
        self.type: Literal["number", "str", None] = None


class HandlerDefine:
    def __init__(self) -> None:
        self.subject_filter_regex: str = None
        self.values: dict = {}


class GroupDefine:
    def __init__(self) -> None:
        self.default: dict | None = {}
        self.handlers: List[HandlerDefine] = []


class PositionDefine:
    def __init__(self) -> None:
        self.table: str | None = None
        self.default: dict | None = {}
        self.groups: List[GroupDefine] = []


class ProductDefine:
    def __init__(self) -> None:
        self.table = None
        self.values = {}


class ExcelConfig:
    def __init__(self) -> None:
        self.subject_code_column = "B"
        self.sheet_name = None
        self.positions = []
        self.product: ProductDefine | None = None
