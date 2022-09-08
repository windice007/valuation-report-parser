import imp
import pyexcel as p
from pyexcel.sheet import Sheet
from prettytable import PrettyTable


START_ROW = 4
START_COLUMN = 1


def display_as_table(array):
    t = PrettyTable()
    t.field_names = array[0]
    t.add_rows(array[1:])
    print(t)


if __name__ == "__main__":
    sheet: Sheet = p.get_sheet(
        file_name="d:/纯固收产品2估值表2021-07-02.xls", start_row=START_ROW, start_column=START_COLUMN, skip_empty_rows=True)
    data = sheet.to_array()
    display_as_table(data)
