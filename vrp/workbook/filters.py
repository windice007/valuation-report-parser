"""Supported valuation-report file filters."""

import os


SUPPORTED_EXTENSIONS = (".xls", ".xlsx", ".csv")


def excel_filter(file: str) -> bool:
    if not os.path.isfile(file):
        return False
    file_name = os.path.basename(file)
    if file_name.startswith("~$"):
        return False
    return file_name.lower().endswith(SUPPORTED_EXTENSIONS)
