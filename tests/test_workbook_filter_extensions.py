from vrp.workbook.filters import excel_filter


def test_workbook_filter_accepts_supported_extensions(tmp_path):
    files = [tmp_path / name for name in ("a.xls", "b.XLSX", "c.csv")]
    for file in files:
        file.write_text("", encoding="utf-8")
    assert all(excel_filter(str(file)) for file in files)
