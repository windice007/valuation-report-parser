from vrp.excel.process import process_excel_file as legacy_process
from vrp.parsing.pipeline import process_excel_file


def test_pipeline_import_keeps_legacy_callable():
    assert process_excel_file is legacy_process
