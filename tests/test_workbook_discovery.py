from pathlib import Path

from vrp.workbook.discovery import current_dir_files


def test_discovery_returns_only_supported_files(tmp_path):
    for name in ("a.xls", "b.csv", "notes.txt"):
        (tmp_path / name).write_text("", encoding="utf-8")
    assert {Path(path).name for path in current_dir_files(str(tmp_path))} == {"a.xls", "b.csv"}
