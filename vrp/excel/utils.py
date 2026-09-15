"""Compatibility imports for configuration JSON helpers."""

from vrp.config.objects import Dict
from vrp.config.serialization import obj_json_default, obj_json_hook

__all__ = ["Dict", "obj_json_default", "obj_json_hook"]
