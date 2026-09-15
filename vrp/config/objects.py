"""Dictionary objects with attribute-style access."""

from typing import Any


class Dict:
    def __init__(self, data: dict | None = None):
        self.data = data if data is not None else {}

    def __getattr__(self, name: str) -> Any:
        if name in self.data:
            return self.data.get(name)
        return None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "data":
            self.__dict__[name] = value
        else:
            self.data[name] = value

    def __iter__(self):
        return iter(self.data.items())

    def __str__(self) -> str:
        from vrp.config.serialization import obj_json_default
        import json
        return json.dumps(self.data, default=obj_json_default, ensure_ascii=False)

    def __contains__(self, element) -> bool:
        return element in self.data
