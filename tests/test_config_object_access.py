from vrp.config.objects import Dict


def test_dict_supports_attribute_read_and_write():
    value = Dict({"before": 1})
    value.after = 2
    assert value.before == 1 and value.data["after"] == 2
