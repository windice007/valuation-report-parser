"""Database connection settings."""

from configparser import RawConfigParser
import os

from vrp.base.logger import logger
from vrp.base.utils import search_app_file


def get_db_connection_url(args):
    if isinstance(args.connection_url, str) and args.connection_url != "":
        return args.connection_url
    settings_file = search_app_file("settings.ini", args.dir)
    if settings_file is None:
        return None
    logger.info(f"加载配置文件：{os.path.abspath(settings_file)}")
    parser = RawConfigParser()
    parser.read(settings_file)
    if parser.has_option("database", "connection_url"):
        return parser.get("database", "connection_url")
    return None


def check_db_settings(args):
    from vrp.excel.sink import check_db_settings as legacy_check
    return legacy_check(args)


__all__ = ["get_db_connection_url", "check_db_settings"]
