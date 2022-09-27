from excel.define import DataCell, ExcelConfig, PositionDefine, ProductDefine, SubjectDefine, ValueDefine


def obj_json_hook(dic: dict):
    obj = None
    if "default" in dic and "subjects" in dic:
        obj = PositionDefine()
    if "code" in dic and "values" in dic:
        obj = SubjectDefine()
    if "cell" in dic and "column" in dic:
        obj = ValueDefine()
    if "address" in dic:
        obj = DataCell()
    if "subject_code_column" in dic and "positions" in dic:
        obj = ExcelConfig()
    if "model" in dic and "values" in dic:
        obj = ProductDefine()
    if obj is None:
        return dic
    else:
        obj.__dict__ = dic
        if isinstance(obj, ValueDefine) and isinstance(obj.cell, str):
            obj.cell = DataCell(obj.cell)
        return obj
