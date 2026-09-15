from vrp.excel.sink import DbSink as LegacyDbSink
from vrp.storage.database import DbSink


def test_database_sink_has_focused_import():
    assert DbSink is LegacyDbSink
