from excel.define import DataCell, ExcelConfig, PositionDefine, SubjectDefine, ValueDefine


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
        if isinstance(obj, ValueDefine) and isinstance(obj.cell, str):
            obj.cell = DataCell(obj.cell)
        return obj
