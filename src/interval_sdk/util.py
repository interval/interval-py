import json, re
from typing import Any, Mapping, Tuple, Callable, TypeAlias
from datetime import date, time, datetime


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


def dict_keys_to_snake(d: dict[str, Any]) -> dict[str, Any]:
    return {camel_to_snake(key): val for (key, val) in d.items()}


def load_snake_pairs(pairs: list[Tuple[str, Any]]) -> dict[str, Any]:
    return {camel_to_snake(key): val for (key, val) in pairs}


def json_loads_some_snake(
    *keys_to_include: str,
) -> Callable:
    """
    Note: this does not recurse.
    """
    camel_keys_to_include = [snake_to_camel(key) for key in keys_to_include]

    def json_loads(*args, **kwargs) -> Any:
        obj = json.loads(*args, **kwargs)
        if isinstance(obj, dict):
            return {
                camel_to_snake(key) if key in camel_keys_to_include else key: val
                for (key, val) in obj.items()
            }

        return obj

    return json_loads


def deserialize_date(val: str):
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except:
            pass

    return val


def json_loads_camel(*args, **kwargs) -> Any:
    return json.loads(
        *args,
        **kwargs,
        object_pairs_hook=load_snake_pairs,
        parse_constant=deserialize_date,
    )


def dump_snake_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        obj = {snake_to_camel(key): dump_snake_obj(val) for (key, val) in obj.items()}
    elif isinstance(obj, list):
        obj = [dump_snake_obj(item) for item in obj]
    elif isinstance(obj, str):
        try:
            return datetime.fromisoformat(obj)
        except:
            pass

    return obj


def dict_strip_none(d: dict[str, Any]) -> dict[str, Any]:
    return {key: val for (key, val) in d.items() if val is not None}


def json_dumps_snake(obj: Any, *args, **kwargs) -> str:
    return json.dumps(dump_snake_obj(obj), *args, **kwargs)


def json_dumps_some_snake(
    *keys_to_include: str,
):
    def json_dumps(obj: Mapping[str, Any], *args, **kwargs) -> str:
        obj = {}
        for key, val in obj.items():
            if key in keys_to_include:
                obj[key] = val
            else:
                obj[snake_to_camel(key)] = dump_snake_obj(val)

        return json.dumps(obj, *args, **kwargs)

    return json_dumps


Deserializable: TypeAlias = int | float | bool | None | str
DeserializableRecord: TypeAlias = Mapping[str, Deserializable]
Serializable: TypeAlias = bool | int | float | datetime | date | str | None
SerializableRecord: TypeAlias = Mapping[str, Serializable]

ObjectLiteral: TypeAlias = int | float | bool | datetime | date | None | str

KeyValueObject: TypeAlias = (
    ObjectLiteral | list["KeyValueObject"] | dict[str, "KeyValueObject"]
)


def ensure_serialized(record: DeserializableRecord):
    for val in record.values():
        if (
            val is not None
            and not isinstance(val, int)
            and not isinstance(val, float)
            and not isinstance(val, bool)
            and not isinstance(val, str)
        ):
            raise ValueError("Invalid value type, must be a primitive.")


def deserialize_dates(
    record: DeserializableRecord | SerializableRecord,
) -> SerializableRecord:
    ret = {}

    for key, val in record.items():
        if isinstance(val, str):
            try:
                ret[key] = datetime.fromisoformat(val)
            except:
                ret[key] = val
        else:
            ret[key] = val

    return ret


def serialize_dates(record: SerializableRecord | None) -> DeserializableRecord | None:
    if record is None:
        return None

    ret = {}

    for key, val in record.items():
        if isinstance(val, datetime) or isinstance(val, date) or isinstance(val, time):
            ret[key] = val.isoformat()
        else:
            ret[key] = val

    return ret
