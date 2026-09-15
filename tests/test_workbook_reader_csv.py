from vrp.workbook.reader import read_sheet


def test_reader_loads_csv_file(tmp_path):
    file = tmp_path / "report.csv"
    file.write_text("code,value\n1001,20\n", encoding="utf-8")
    sheet = read_sheet(str(file))
    assert sheet.cell_value(1, 0) == 1001
