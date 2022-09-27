import json
from excel import process_excel_file_data as process, ExcelConfig, DataCell
from excel.define import PositionDefine, SubjectDefine, ValueDefine
from excel.utils import obj_json_hook


if __name__ == "__main__":

    file = "d:/纯固收产品2估值表2021-07-02.xls"
    with open('config.json', 'r', encoding="utf-8") as f:
        config = json.load(f, object_hook=obj_json_hook)
        vpd = process(file, config)
        print(vpd)
