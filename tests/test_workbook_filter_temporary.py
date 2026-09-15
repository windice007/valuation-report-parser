from vrp.workbook.filters import excel_filter


def test_workbook_filter_rejects_excel_temporary_file(tmp_path):
    file = tmp_path / "~$report.xlsx"
    file.write_text("", encoding="utf-8")
    assert not excel_filter(str(file))
