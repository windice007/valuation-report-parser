from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

import pytest
from sqlalchemy import Column, Integer, MetaData, Numeric, String, Table, create_engine, select

from vrp.excel.process import (
    create_model,
    convert_str_to_decimal,
    convert_value,
    formula_eval,
    process_data,
    safe_float,
)
from vrp.excel.utils import Dict


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


@pytest.mark.parametrize("value", [None, "", "   ", "\t", "\u00a0", "\u3000"])
@pytest.mark.parametrize("nullable", [True, False])
def test_blank_number_field_uses_nullability(value, nullable):
    expected = None if nullable else Decimal(0)
    assert convert_value(value, "number", nullable=nullable) == expected


def test_number_field_without_schema_defaults_to_null():
    context = SimpleNamespace(current_model=None, env={}, current_row=None)
    process_data(context, Dict({"amount": Dict({"value": "  ", "type": "number"})}))
    assert list(context.env.values()) == [None]


@pytest.mark.parametrize("value", [None, "", " \t\u00a0\u3000", "0", "- 2,440,767.12"])
def test_database_number_columns_use_reflected_nullability(value):
    engine = create_engine("sqlite://")
    try:
        table = Table(
            "amounts", MetaData(),
            Column("id", Integer, primary_key=True),
            Column("required_amount", Numeric(18, 2), nullable=False),
            Column("optional_amount", Numeric(18, 2), nullable=True, server_default="99"),
            Column("note", String),
        )
        table.create(engine)
        reflected = Table("amounts", MetaData(), autoload_with=engine)
        context = SimpleNamespace(
            current_model=create_model("amounts"), env={},
            sink=SimpleNamespace(db_sink=SimpleNamespace(get_table=lambda name: reflected)),
        )
        process_data(context, Dict({
            "REQUIRED_AMOUNT": value, "optional_amount": value, "note": "  ",
        }))
        required = context.current_model["required_amount"]
        optional = context.current_model["optional_amount"]
        blank = value is None or not value.strip()
        expected = Decimal(0) if blank else convert_str_to_decimal(value)
        assert required == expected
        assert optional == (None if blank else expected)
        assert context.current_model["note"] == "  "
        with engine.begin() as connection:
            connection.execute(table.insert().values(
                id=1, required_amount=required, optional_amount=optional,
            ))
            row = connection.execute(select(table)).mappings().one()
        assert row["required_amount"] == expected
        assert row["optional_amount"] == (None if blank else expected)
    finally:
        engine.dispose()
