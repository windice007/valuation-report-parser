"""Read workbooks and handle known malformed-file variants."""

import os
import shutil
from tempfile import TemporaryDirectory

import pyexcel

from vrp.base.logger import logger


def stylesheet_fix(func):
    def wrapper(*args, **kwargs):
        kwargs["fills"] = [item for item in kwargs["fills"] if item is not None]
        return func(*args, **kwargs)
    return wrapper


def read_sheet(file: str, sheet_name: str | None = None):
    try:
        return pyexcel.get_sheet(file_name=file, sheet_name=sheet_name)
    except NotImplementedError:
        with TemporaryDirectory(prefix="vrp-") as tmp_dir:
            tmp_file = os.path.join(tmp_dir, os.path.basename(file) + "x")
            logger.info(f"read file_name<{file}> fail, try read file<{tmp_file}>")
            shutil.copyfile(file, tmp_file)
            return pyexcel.get_sheet(file_name=tmp_file, sheet_name=sheet_name)
    except TypeError as err:
        if err.args and err.args[0] == "expected <class 'openpyxl.styles.fills.Fill'>":
            from openpyxl.styles.stylesheet import Stylesheet
            Stylesheet.__init__ = stylesheet_fix(Stylesheet.__init__)
            return pyexcel.get_sheet(file_name=file, sheet_name=sheet_name)
        raise
