"""Argument parser construction for the main command."""

import argparse

from vrp import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="估值表解析程序")
    parser.add_argument("-v", "--version", action="version", version=__version__, help="display app version.")
    parser.add_argument("dir", nargs="?", default=".", type=str, help="指定工作目录或估值表文件。")
    parser.add_argument("-c", "--config", default="config.json", type=str, help="指定配置文件")
    parser.add_argument("--connection_url", default="", type=str, help="指定目标数据库的链接字符串")
    parser.add_argument("--nofile", action="store_true", default=False, help="不生成结果文件。")
    parser.add_argument("--debug", action="store_true", default=False, help="启用debug模式，会输出更多信息。")
    return parser
