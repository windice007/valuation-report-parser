from datetime import datetime

from vrp.config.serialization import obj_json_default


def test_datetime_keeps_time_when_present():
    value = datetime(2026, 9, 16, 8, 30, 5)
    assert obj_json_default(value) == "2026-09-16 08:30:05"
