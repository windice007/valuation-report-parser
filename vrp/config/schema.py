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
    """
    subject_filter_regex: 当前Handler处理数据时，会过滤掉科目代码不匹配这个正则的行。
    """
    start_row: int
    """
    start_row: 当前Handler处理的开始行号，不设置程序会从第一行开始处理。
    """
    stop_row: int | None
    """
    stop_row: 当前Handler处理的结束行号，不设置程序会处理所有可处理的行。
    """
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
    """
    subject_code_column: 重要设置，设置科目代码列。也是后续过滤以及定位数据的重要属性。原则上，这一列的数据是不可重复的。
    """
    spare_subject_code_column: str | None
    """
    spare_subject_code_column: 设置备用科目代码列。当subject_code_column配置的列获取的科目代码为空时，会使用备用科目代码列的数据，在某些特殊的估值表格式会需要设置这个值。
    """
    raise_index_out_range_error: bool | None
    sheet_name: str | None
    """
    sheet_name: 设置Excel的sheet名称，当估值表文件不仅一个sheet的时候使用。
    """
    env: dict | None
    """
    env: 一个字典结构，预设或者从Excel中抓取的全局数据，可以在后续的formula配置中引用。
    """
    positions: List[PositionDefine] | None
    """
    positions: 处理持仓的配置列表。
    """
    products: List[ProductDefine] | None
    """
    products: 处理产品数据的配置列表。
    """
