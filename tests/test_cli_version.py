from vrp import __version__
from vrp.cli.version import version_text


def test_cli_version_uses_package_version():
    assert version_text() == __version__
