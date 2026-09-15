from vrp.cli.discovery import excel_filter


def test_cli_discovery_uses_workbook_filter(tmp_path):
    file = tmp_path / "report.csv"
    file.write_text("", encoding="utf-8")
    assert excel_filter(str(file))
