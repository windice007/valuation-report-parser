import json
from excel import process_excel_file_data as process, ExcelConfig, DataCell
from excel.define import PositionDefine, SubjectDefine, ValueDefine


def obj_json_default(obj):
    return obj.__dict__


def obj_json_hook(dic: dict):
    obj = None
    if "default" in dic and "subjects" in dic:
        obj = PositionDefine()
    if "code" in dic and "values" in dic:
        obj = SubjectDefine()
    if "cell" in dic and "column" in dic:
        obj = ValueDefine()
    if "address" in dic and "capture_regex" in dic:
        obj = DataCell()
    if "start_row" in dic and "global_data" in dic:
        obj = ExcelConfig()
    if obj is None:
        return dic
    else:
        obj.__dict__ = dic
        return obj


if __name__ == "__main__":

    file = "d:/纯固收产品2估值表2021-07-02.xls"
    with open('config.json', 'r', encoding="utf-8") as f:
        config = json.load(f, object_hook=obj_json_hook)
        vpd = process(file, config)
        print(vpd)
