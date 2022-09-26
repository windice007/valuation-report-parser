from excel import process_excel_file_data as process, ExcelConfig, DataCell
from excel.define import PositionDefine, SubjectDefine, ValueDefine

if __name__ == "__main__":

    file = "d:/纯固收产品2估值表2021-07-02.xls"

    config = ExcelConfig()
    config.start_row = 1
    config.global_data["valuation_date"] = DataCell("A3")
    config.global_data["product_code"] = DataCell("A1", "^(\w+)资产估值表")
    config.BUSIPOSBOND = []

    d1 = PositionDefine()
    d1.default = {
        "AMT": 100.2
    }
    d1.subjects = []

    s1 = SubjectDefine()
    s1.code = "11030401"
    s1.values = []

    v1 = ValueDefine()
    v1.cell = DataCell("C")
    v1.column = "SYMBOL"
    s1.values.append(v1)

    v1 = ValueDefine()
    v1.cell = DataCell("D")
    v1.column = "CURRENCY"
    s1.values.append(v1)

    d1.subjects.append(s1)
    config.BUSIPOSBOND.append(d1)

    vpd = process(file, config)

    print()
