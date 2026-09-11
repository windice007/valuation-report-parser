from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

import pytest

from vrp.excel.process import (
    convert_str_to_decimal,
    convert_value,
    formula_eval,
    safe_float,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("- 2,440,767.12", "-2440767.12"),
        ("+ 2,440,767.12", "2440767.12"),
        ("  -   2,440,767.12  ", "-2440767.12"),
        ("\t-\t2,440,767.12\t", "-2440767.12"),
        ("\u00a0-\u00a02,440,767.12\u00a0", "-2440767.12"),
        ("\u3000-\u30002,440,767.12\u3000", "-2440767.12"),
        ("123.45", "123.45"),
        ("-123.45", "-123.45"),
        ("2,440,767.12", "2440767.12"),
        ("12.5%", "0.125"),
        ("  - 12.5%  ", "-0.125"),
        ("", "0"),
        (" \t\u00a0\u3000", "0"),
    ],
)
def test_numeric_strings(value, expected):
    result = convert_str_to_decimal(value)
    assert isinstance(result, Decimal)
    assert result == Decimal(expected)


@pytest.mark.parametrize(
    "value",
    ["1 234.56", "1\u00a0234.56", "- 2 440.12", "--12", "- +12", "abc", "-"],
)
def test_invalid_numeric_strings(value):
    with pytest.raises(InvalidOperation):
        convert_str_to_decimal(value)


def test_number_field_conversion():
    assert convert_value("- 2,440,767.12", "number") == Decimal("-2440767.12")


def test_formula_decimal_conversion():
    context = SimpleNamespace(current_model={}, env={})
    result = formula_eval(context, 'Decimal("- 2,440,767.12")', {})
    assert result == Decimal("-2440767.12")


def test_safe_float_keeps_invalid_value_fallback(monkeypatch):
    warnings = []
    monkeypatch.setattr("vrp.excel.process.logger.warn", warnings.append)
    assert safe_float("1 234.56") == Decimal(0)
    assert warnings == ["Decimal转换失败：1 234.56"]
