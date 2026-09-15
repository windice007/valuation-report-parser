from vrp.excel.process import ProcessContext as LegacyContext
from vrp.parsing.context import ProcessContext


def test_context_has_stable_focused_import():
    assert ProcessContext is LegacyContext
