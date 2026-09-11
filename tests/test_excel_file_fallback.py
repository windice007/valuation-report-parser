from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pyexcel
import pytest
from openpyxl import Workbook

from vrp.excel.process import process_excel_file
from vrp.excel.utils import Dict


@pytest.mark.parametrize("fallback_fails", [False, True])
def test_format_fallback_preserves_existing_workbooks(tmp_path, monkeypatch, fallback_fails):
    existing = tmp_path / "report.xlsx"
    workbook = Workbook()
    workbook.active.append(["1001", "test"])
    workbook.save(existing)
    workbook.close()
    source = tmp_path / "report.xls"
    source.write_bytes(existing.read_bytes())
    existing.write_bytes(b"independent existing workbook")
    original_source = source.read_bytes()
    original_existing = existing.read_bytes()

    read_sheet = pyexcel.get_sheet
    temporary_files = []

    def get_sheet(*, file_name, sheet_name):
        if file_name == str(source):
            raise NotImplementedError("retry with xlsx extension")
        temporary = Path(file_name)
        temporary_files.append(temporary)
        assert temporary.suffix == ".xlsx"
        assert temporary.read_bytes() == original_source
        assert existing.read_bytes() == original_existing
        if fallback_fails:
            raise RuntimeError("fallback read failed")
        return read_sheet(file_name=file_name, sheet_name=sheet_name)

    monkeypatch.setattr(pyexcel, "get_sheet", get_sheet)
    config = Dict({"subject_code_column": "A"})
    sink = Mock()
    args = SimpleNamespace(debug=False)

    if fallback_fails:
        with pytest.raises(RuntimeError, match="fallback read failed"):
            process_excel_file(str(source), config, args, sink)
        sink.save.assert_not_called()
    else:
        process_excel_file(str(source), config, args, sink)
        sink.save.assert_called_once()
        assert sink.save.call_args.args[0].file == str(source)

    assert source.read_bytes() == original_source
    assert existing.read_bytes() == original_existing
    assert len(temporary_files) == 1
    assert not temporary_files[0].exists()
    assert not temporary_files[0].parent.exists()
