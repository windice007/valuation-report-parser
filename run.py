from asyncio.windows_events import NULL
import pyexcel as p
from pyexcel.sheet import Sheet
from prettytable import PrettyTable
from excel import process_excel_file_data as process

START_ROW = 4
START_COLUMN = 1


def display_as_table(array: list[list]):
    t = PrettyTable()
    t.add_rows(array)
    print(t)


if __name__ == "__main__":

    file = "d:/纯固收产品2估值表2021-07-02.xls"
    sheet: Sheet = process(file)

    data = sheet.to_array()
    display_as_table(data)
