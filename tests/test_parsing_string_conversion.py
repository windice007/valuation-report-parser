from vrp.parsing.conversion import convert_value


def test_string_conversion_preserves_none():
    assert convert_value(None, "str") is None
    assert convert_value(123, "str") == "123"
