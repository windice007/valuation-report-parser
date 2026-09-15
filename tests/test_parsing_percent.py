from decimal import Decimal

from vrp.parsing.numbers import convert_str_to_decimal


def test_percent_is_converted_to_ratio():
    assert convert_str_to_decimal("25%") == Decimal("0.25")
