"""Locate configuration files using application search precedence."""

from vrp.base.utils import search_app_file


def locate_config(file_name: str, work_dir: str) -> str | None:
    return search_app_file(file_name, work_dir)
