from asyncio.windows_events import NULL
import pyexcel as p
from pyexcel.sheet import Sheet
from prettytable import PrettyTable
from excel import process_excel_file_data as process, ExcelConfig, DataCell
from excel.define import PositionDefine, SubjectDefine, ValueDefine

START_ROW = 4
START_COLUMN = 1


def display_as_table(array: list[list]):
    t = PrettyTable()
    t.add_rows(array)
    print(t)


if __name__ == "__main__":

    file = "d:/纯固收产品2估值表2021-07-02.xls"

    config = ExcelConfig()
    config.start_column = 4
    config.start_row = 1
    config.valuation_date = DataCell("A3")
    config.product_code = DataCell("A1", "^(\w+)资产估值表")
    config.pos_bond_define = []

    d1 = PositionDefine()
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
    config.pos_bond_define.append(d1)

    vpd = process(file, config)

    print()
