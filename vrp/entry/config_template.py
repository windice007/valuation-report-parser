"""根据数据库中表字段，生成估值表解析配置模板。"""
from argparse import ArgumentParser
from vrp import Args
from vrp.excel.define import ExcelConfig
from vrp.excel.sink import MultiSink


def set_parser(parser: ArgumentParser):
    parser.add_argument(
        "--connection_url", default="", type=str, help="指定目标数据库的链接字符串", required=True
    )
    parser.add_argument("--position_tables", default=None, type=str, help="指定目标持仓表清单")
    parser.add_argument("--product_table", default=None, type=str, help="指定目标产品指标表")


def process(args):
    pass
