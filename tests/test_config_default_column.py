from vrp.config.defaults import init_config
from vrp.config.objects import Dict


def test_missing_subject_column_defaults_to_a():
    config = init_config(Dict())
    assert config.subject_code_column == "A"
