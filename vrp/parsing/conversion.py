"""Convert captured values to configured target types."""

from decimal import Decimal

from vrp.config.schema import Target_Type
from vrp.parsing.dates import convert_int_to_datetime, convert_str_to_date, convert_str_to_datetime
from vrp.parsing.numbers import convert_str_to_decimal


def convert_any_to_str(value) -> str | None:
    return None if value is None else str(value)


def convert_value(value, target: Target_Type, nullable: bool = True):
    if target == "number" and (value is None or (isinstance(value, str) and not value.strip())):
        return None if nullable else Decimal(0)
    if isinstance(value, str):
        if target == "number":
            return convert_str_to_decimal(value)
        if target == "date":
            return convert_str_to_date(value)
        if target == "datetime":
            return convert_str_to_datetime(value)
    if isinstance(value, int):
        if target == "date":
            return convert_int_to_datetime(value).date()
        if target == "datetime":
            return convert_int_to_datetime(value)
    if target == "str":
        return convert_any_to_str(value)
    return value
