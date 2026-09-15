from io import StringIO
from types import SimpleNamespace

from vrp.config.loader import load_config_file


def test_stream_configuration_is_loaded_and_defaulted():
    config = load_config_file(SimpleNamespace(config=StringIO("{}"), dir="."))
    assert config.subject_code_column == "A"
