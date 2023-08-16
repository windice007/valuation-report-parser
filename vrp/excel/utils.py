from typing import Any


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
        return str(self.data)

    def __contains__(self, element) -> bool:
        return element in self.data


def obj_json_hook(dic: dict):
    return Dict(dic)
