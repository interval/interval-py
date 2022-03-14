import json, re
from typing import Any


from pydantic import BaseModel as PydanticBaseModel
from pydantic.generics import GenericModel as PydanticGenericModel


def snake_to_camel(s: str) -> str:
    return "".join(
        word.capitalize() if i > 0 else word for (i, word) in enumerate(s.split("_"))
    )


# From https://stackoverflow.com/a/1176023
camel_p1 = re.compile("(.)([A-Z][a-z]+)")
camel_p2 = re.compile("([a-z0-9])([A-Z])")


def camel_to_snake(name: str) -> str:
    name = camel_p1.sub(r"\1_\2", name)
    return camel_p2.sub(r"\1_\2", name).lower()


def json_loads_camel(s: str, **kwargs) -> Any:
    obj = json.loads(s, **kwargs)
    return {camel_to_snake(key): val for (key, val) in obj}


def json_dumps_camel(obj: Any, **kwargs) -> str:
    if isinstance(obj, dict):
        obj = {snake_to_camel(key): val for (key, val) in obj.items()}

    return json.dumps(obj, **kwargs)


class BaseModel(PydanticBaseModel):
    class Config:
        json_loads = json_loads_camel
        json_dumps = json_dumps_camel


class GenericModel(PydanticGenericModel):
    class Config:
        json_loads = json_loads_camel
        json_dumps = json_dumps_camel
