from decimal import Decimal

from vrp.config.serialization import obj_json_default


def test_decimal_is_serialized_as_number():
    assert obj_json_default(Decimal("12.50")) == 12.5
