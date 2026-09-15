from vrp.config.defaults import init_config
from vrp.config.objects import Dict


def test_bounds_errors_are_enabled_by_default():
    assert init_config(Dict()).raise_index_out_range_error is True
