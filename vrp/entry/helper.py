"""
helper
"""
from argparse import ArgumentParser
from typing import Protocol
from vrp.base.utils import excel_column_index
from vrp.excel.define import ExcelConfig

from vrp.run import load_config_file, current_dir_files


from vrp.base.logger import logger

import pyexcel
import re


__version__: str = "0.0.1"

__PROG__: str = "gen_code"


class Args(Protocol):
    dir: str
    debug: bool
    config: str


def set_parser(parser: ArgumentParser):
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
        help="display app version.",
    )
    parser.add_argument(
        "dir",
        nargs="?",
        default=".",
        type=str,
        help="指定工作目录，程序会在工作目录中检索可用的估值表文件。如果不设定，默认为当前工作目录。",
    )
    parser.add_argument(
        "-c", "--config", default="config.json", type=str, help="指定配置文件"
    )


def process(args: Args):
    files = current_dir_files(args.dir)
    config = load_config_file(args)

    result = {}

    for file in files:
        process_excel_file(file, config, result)

    records = list(result.values())
    pyexcel.save_as(records=records, dest_file_name="code.xlsx")


def process_excel_file(file, config: ExcelConfig, result: dict):
    logger.info(f"开始处理估值文件：{file}")
    sheet = pyexcel.get_sheet(file_name=file, sheet_name=config.sheet_name)

    for i in range(len(sheet)):
        code = sheet.cell_value(i, excel_column_index(config.subject_code_column))
        if code == "" or code == None:
            continue
        name = sheet.cell_value(i, excel_column_index("B"))

        if re.fullmatch("\\d{4,}", code):
            result[code] = {
                "code": code,
                "name": name,
                "file": file,
                "is": len(code) == 14,
            }
