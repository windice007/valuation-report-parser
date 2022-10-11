import json

from base.db_mysql import obj_json_default
from excel import process_excel_file_data as process
from excel.utils import obj_json_hook
import pyexcel_xls
import pyexcel_xlsx
import pyexcel_io.writers
import os
import glob


def current_dir_files():
    return glob.glob("*.xls")+glob.glob("*.xlsx")


if __name__ == "__main__":
    with open('config.json', 'r', encoding="utf-8") as f:
        config = json.load(f, object_hook=obj_json_hook)

        files = current_dir_files()

        if len(files) == 0:
            print("当前目录没有找到估值文件(*.xls|*.xlsx)")

        for file in current_dir_files():
            vpd = process(file, config)
            with open(f'{file}.json', 'w', encoding="utf-8") as writer:
                json.dump({"positions": list(vpd.details.values()), "product": vpd.product}, writer,  default=obj_json_default,
                          indent=2, ensure_ascii=False)
