"""Load JSON parser configuration from streams or files."""

from io import TextIOBase
import json
import os

from vrp.base.logger import logger
from vrp.config.defaults import init_config
from vrp.config.locator import locate_config
from vrp.config.serialization import obj_json_hook


def load_config_file(args):
    if isinstance(args.config, TextIOBase):
        return init_config(json.loads(args.config.read(), object_hook=obj_json_hook))
    file = locate_config(args.config, args.dir)
    if file is None:
        return None
    logger.info(f"加载配置文件：{os.path.abspath(file)}")
    with open(file, "r", encoding="utf-8") as stream:
        return init_config(json.load(stream, object_hook=obj_json_hook))
