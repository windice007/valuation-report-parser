from decimal import Decimal

from vrp.parsing.numbers import convert_str_to_decimal


def test_blank_numeric_text_becomes_zero():
    assert convert_str_to_decimal("  ") == Decimal(0)
