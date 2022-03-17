import json, re
from typing import Any, Tuple


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


def dict_keys_to_camel(d: dict[str, Any]) -> dict[str, Any]:
    return {snake_to_camel(key): val for (key, val) in d.items()}


def load_camel_pairs(pairs: list[Tuple[str, Any]]) -> dict[str, Any]:
    return {camel_to_snake(key): val for (key, val) in pairs}


def json_loads_camel(*args, **kwargs) -> Any:
    return json.loads(*args, **kwargs, object_pairs_hook=load_camel_pairs)


def dump_snake_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        obj = {snake_to_camel(key): dump_snake_obj(val) for (key, val) in obj.items()}

    return obj


def json_dumps_camel(obj: Any, *args, **kwargs) -> str:
    return json.dumps(dump_snake_obj(obj), *args, **kwargs)


class BaseModel(PydanticBaseModel):
    class Config:
        json_loads = json_loads_camel
        json_dumps = json_dumps_camel


class GenericModel(PydanticGenericModel):
    class Config:
        json_loads = json_loads_camel
        json_dumps = json_dumps_camel
