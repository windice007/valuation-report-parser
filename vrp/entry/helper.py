"""
helper
"""
from vrp.base.utils import excel_column_index
from vrp.excel.define import ExcelConfig


from vrp.base.logger import logger
from vrp import Args, __version__

import pyexcel
import re

from vrp.excel.sink import MultiSink


def process(files: list[str], config: ExcelConfig, args: Args, sink: MultiSink):
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
