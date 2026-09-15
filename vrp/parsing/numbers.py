"""Numeric parsing used by cells and formulas."""

from decimal import Decimal
import re

from vrp.base.logger import logger


def convert_str_to_decimal(value: str) -> Decimal:
    value = re.sub(r"^([+-])\s+", r"\1", value.strip())
    value = value.replace(",", "")
    if value == "":
        return Decimal(0)
    if value.endswith("%"):
        return Decimal(value.rstrip("%")) / 100
    return Decimal(value)


def safe_float(value):
    try:
        if isinstance(value, str):
            return convert_str_to_decimal(value)
        return Decimal(value)
    except Exception:
        logger.warning("Decimal转换失败：%s", value)
        return Decimal(0)
