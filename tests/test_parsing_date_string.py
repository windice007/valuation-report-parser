from datetime import date

from vrp.parsing.dates import convert_str_to_date


def test_text_date_is_parsed():
    assert convert_str_to_date("2026-09-16") == date(2026, 9, 16)
