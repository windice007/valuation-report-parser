from decimal import Decimal

from vrp.parsing.conversion import convert_value


def test_required_blank_number_becomes_zero():
    assert convert_value(" ", "number", nullable=False) == Decimal(0)
