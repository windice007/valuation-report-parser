from typing import Any, List, Literal, Protocol

Target_Type = Literal["number", "str", "date", "datetime"]
MERGED_VALUE_TYPE = Literal["up", "down", "left", "right", "auto"]


class DataCell(Protocol):
    address: str
    capture_regex: str
    subject_code: str
    mapping: dict
    mapping_rule: Literal["contains", "equals", "regex", None]
    formula: str
    type: Target_Type | None
    subject_filter_regex: str | None
    filter_formula: str | None
    value: Any
    merged_value: MERGED_VALUE_TYPE | None


class HandlerDefine(Protocol):
    subject_filter_regex: str
    start_row: int
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
    spare_subject_code_column: str | None
    raise_index_out_range_error: bool | None
    sheet_name: str | None
    env: dict | None
    positions: List[PositionDefine] | None
    products: List[ProductDefine] | None
