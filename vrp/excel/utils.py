from typing import Any


class Dict:
    def __init__(self, data: dict):
        self.data = data

    def __getattr__(self, __name: str) -> Any:
        if __name in self.data:
            return self.data.get(__name)
        return None

    def __iter__(self):
        return iter(self.data.items())


def obj_json_hook(dic: dict):
    return Dict(dic)
