"""JSON conversion for parser configuration and results."""

from datetime import date, datetime
import decimal

from vrp.config.objects import Dict


def obj_json_hook(data: dict):
    return Dict(data)


def obj_json_default(obj):
    if type(obj) is Dict:
        return obj.data
    if type(obj) is decimal.Decimal:
        return float(obj)
    if type(obj) is datetime:
        if obj.hour == 0 and obj.minute == 0 and obj.second == 0:
            return obj.strftime("%Y-%m-%d")
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    if type(obj) is date:
        return obj.strftime("%Y-%m-%d")
    return obj
