from typing import Any, List, Literal, Protocol

Target_Type = Literal["number", "str", "date", "datetime"]
MERGED_VALUE_TYPE = Literal["up", "down", "left", "right", "auto"]


class DataCell(Protocol):
    """
    属性数据配置
    """

    address: str
    """
    address: 地址配置，针对Excel，可以配置为绝对地址（行和列都配置，如'A3'）和相对地址(只配置列，如'A')，相对地址只能用在position配置中
    """
    capture_regex: str
    """
    capture_regex: 获取数据的正则表达式，如果不设置就是原始数据。
    """
    subject_code: str
    """
    subject_code: 基于科目代码来定位和获取数据，相当于间接设置行
    """
    mapping: dict
    """
    mapping: 数据转换规则配置
    """
    mapping_rule: Literal["contains", "equals", "regex", None]
    """
    mapping_rule: 数据转换规则模式的配置，默认为equals
    可以设置的选项为: ["contains", "equals", "regex"]
    """
    formula: str
    """
    formula: 通过表达式来返回数据
    """
    type: Target_Type | None
    """
    type: 数据的类型设置，如果配置了数据库连接，引擎会自动根据数据库字段类型来进行判断，无需设置。
    可以设置的选项为: ["number", "str", "date", "datetime"]
    """
    subject_filter_regex: str | None
    filter_formula: str | None
    value: Any
    merged_value: MERGED_VALUE_TYPE | None
    """
    merged_value: 数据如果为空，可以设置进行单元格数据合并，自动获取上下左右第一个部位空的数据作为有效数据返回。
    可以设置的选项为: ["up", "down", "left", "right", "auto"]
    """


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
