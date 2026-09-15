from types import SimpleNamespace

from vrp.cli.tool_parser import command_name


def test_command_name_prefers_configured_program_name():
    module = SimpleNamespace(__PROG__="codes", __file__="helper.py")
    assert command_name(module) == "codes"
