"""Find valuation-report files in a directory."""

import os

from vrp.workbook.filters import excel_filter


def current_dir_files(directory: str) -> list[str]:
    paths = (os.path.join(directory, name) for name in os.listdir(directory))
    return list(filter(excel_filter, paths))
