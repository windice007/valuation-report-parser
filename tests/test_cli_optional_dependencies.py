import json
import subprocess
import sys

import pytest


def run_without_gauss(module, *args):
    return subprocess.run(
        [sys.executable, "-c", (
            "import runpy, sys\n"
            "class MissingGauss:\n"
            "    def find_spec(self, fullname, path=None, target=None):\n"
            "        if fullname == 'opengauss_sqlalchemy':\n"
            "            raise ModuleNotFoundError('No module named ' + fullname, name=fullname)\n"
            "sys.meta_path.insert(0, MissingGauss())\n"
            "module = sys.argv.pop(1)\n"
            "runpy.run_module(module, run_name='__main__')\n"
        ), module, *args],
        capture_output=True, text=True, timeout=30,
    )


@pytest.mark.parametrize("module", ["vrp.run", "vrp.tools"])
def test_cli_help_without_gauss(module):
    result = run_without_gauss(module, "--help")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "--help" in result.stdout


@pytest.mark.parametrize("driver_source, expected_error", [
    ("import builtins; builtins.gauss_driver_loaded = True", None),
    ("raise ModuleNotFoundError('missing driver dependency', name='driver_dependency')",
     "ModuleNotFoundError: missing driver dependency"),
    ("raise ImportError('broken driver')", "ImportError: broken driver"),
])
def test_installed_gauss_is_imported_and_errors_propagate(tmp_path, driver_source, expected_error):
    package = tmp_path / "opengauss_sqlalchemy"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "psycopg2.py").write_text(driver_source, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", (
            "import builtins, sys; "
            "sys.path.insert(0, sys.argv[1]); "
            "import vrp.run; "
            "assert builtins.gauss_driver_loaded"
        ), str(tmp_path)],
        capture_output=True, text=True, timeout=30,
    )
    if expected_error is None:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0
        assert expected_error in result.stderr


def test_file_parsing_without_gauss(tmp_path):
    source = tmp_path / "report.csv"
    source.write_text("1001,123.45\n", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "subject_code_column": "A",
        "products": [{"table": "products", "values": {
            "amount": {"address": "B1", "type": "number"},
        }}],
    }), encoding="utf-8")
    result = run_without_gauss("vrp.run", str(source), "--config", str(config))
    assert result.returncode == 0, result.stdout + result.stderr
    output = json.loads((tmp_path / "report.csv.json").read_text(encoding="utf-8"))
    assert output["products"][0]["amount"] == 123.45
