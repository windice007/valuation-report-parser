"""Tool subcommand naming."""

import os


def command_name(module) -> str:
    configured = getattr(module, "__PROG__", None)
    if configured:
        return configured
    return os.path.splitext(os.path.basename(module.__file__))[0]
