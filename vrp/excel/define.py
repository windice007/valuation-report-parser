from typing import Any, List, Literal, Protocol


class DataCell(Protocol):
    address: str
    capture_regex: str
    subject_code: str
    mapping: dict
    mapping_rule: Literal["contains", "equals", "regex", None]
    formula: str
    type: Literal["number", "str", None]
    subject_filter_regex: str | None
    filter_formula: str | None
    value: Any


class HandlerDefine(Protocol):
    subject_filter_regex: str
    merge_keys: List[str]
    values: dict
    post_filter_formula: str | None


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


class ExcelConfig(Protocol):
    subject_code_column: str
    sheet_name: str | None
    positions: List[PositionDefine] | None
    products: List[ProductDefine] | None
