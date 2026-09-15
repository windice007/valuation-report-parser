from datetime import datetime

from vrp.parsing.dates import convert_int_to_datetime


def test_compact_integer_datetime_is_parsed():
    assert convert_int_to_datetime(20260916083005) == datetime(2026, 9, 16, 8, 30, 5)
