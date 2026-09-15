from vrp.config.objects import Dict
from vrp.config.validation import config_errors, is_valid_config


def test_config_validation_reports_invalid_shapes():
    config = Dict({"subject_code_column": "A1", "positions": {}, "products": {}})
    errors = config_errors(config)
    assert len(errors) == 3
    assert not is_valid_config(config)
