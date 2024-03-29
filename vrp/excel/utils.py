from datetime import date, datetime
import decimal
from typing import Any
import json


class Dict:
    def __init__(self, data: dict = None):
        self.data = data if data is not None else {}

    def __getattr__(self, __name: str) -> Any:
        if __name in self.data:
            return self.data.get(__name)
        return None

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name == "data":
            self.__dict__[__name] = __value
        else:
            self.data[__name] = __value

    def __iter__(self):
        return iter(self.data.items())

    def __str__(self) -> str:
        return json.dumps(self.data, default=obj_json_default, ensure_ascii=False)

    def __contains__(self, element) -> bool:
        return element in self.data


def obj_json_hook(dic: dict):
    return Dict(dic)


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
