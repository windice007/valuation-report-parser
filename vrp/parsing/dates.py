"""Date and datetime conversion."""

from datetime import date, datetime

from dateutil.parser import parse as parse_date


def convert_str_to_datetime(value: str) -> datetime | None:
    return None if value == "" else parse_date(value)


def convert_str_to_date(value: str) -> date | None:
    result = convert_str_to_datetime(value)
    return result.date() if result is not None else None


def convert_int_to_datetime(value: int) -> datetime:
    if 20000000 < value < 29999999:
        return datetime(value // 10000, (value % 10000) // 100, value % 100)
    if 20000000000000 < value < 29990000000000:
        return datetime(
            value // 10000000000,
            (value % 10000000000) // 100000000,
            (value % 100000000) // 1000000,
            (value % 1000000) // 10000,
            (value % 10000) // 100,
            value % 100,
        )
    return datetime.fromtimestamp(value)
