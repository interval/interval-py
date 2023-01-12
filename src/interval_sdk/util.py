import json, re
from typing import Any, Iterable, Mapping, Optional, Tuple, Callable, Union, cast
from datetime import date, time, datetime
from typing_extensions import TypeAlias, TypeVar

from pydantic import StrictBool, StrictFloat, StrictInt


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
    if not isinstance(d, dict):
        return d

    return {snake_to_camel(key): val for (key, val) in d.items()}


T = TypeVar("T")


def dict_keys_to_snake(d: T) -> T:
    if d is None:
        return d

    if isinstance(d, list):
        return cast(T, [dict_keys_to_snake(i) for i in d])

    if isinstance(d, dict):
        return cast(T, {camel_to_snake(key): val for (key, val) in d.items()})

    return d


def load_snake_pairs(pairs: list[Tuple[str, Any]]) -> dict[str, Any]:
    if not isinstance(pairs, list):
        return pairs

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


def dict_strip_none(
    d: dict[str, Any], keys_to_consider: Optional[Iterable[str]] = None
) -> dict[str, Any]:
    ret = {}

    for key, val in d.items():
        if (keys_to_consider is None or key in keys_to_consider) and val is None:
            continue
        ret[key] = val

    return ret


def json_dumps_strip_none(obj: Any, *args, **kwargs) -> str:
    if isinstance(obj, dict):
        obj = dict_strip_none(obj)

    return json.dumps(obj, *args, **kwargs)


def json_dumps_strip_some_none(*keys_to_include: str):
    def json_dumps(obj: Mapping[str, Any], *args, **kwargs) -> str:
        if isinstance(obj, dict):
            obj = dict_strip_none(obj, keys_to_consider=keys_to_include)

        return json.dumps(obj, *args, **kwargs)

    return json_dumps


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


def json_dumps_snake_strip_none(obj: Any, *args, **kwargs) -> str:
    return json.dumps(dict_keys_to_snake(dict_strip_none(obj)), *args, **kwargs)


def json_loads_snake_strip_none(*args, **kwargs) -> Any:
    obj = json.loads(*args, **kwargs)
    return dict_keys_to_snake(dict_strip_none(obj))


Deserializable: TypeAlias = Union[int, float, bool, None, str]
DeserializableRecord: TypeAlias = Mapping[str, Deserializable]
Serializable: TypeAlias = Union[bool, int, float, datetime, date, time, str, None]
SerializableRecord: TypeAlias = Mapping[str, Serializable]

ObjectLiteral: TypeAlias = Union[
    StrictInt, StrictFloat, StrictBool, datetime, date, time, None, str
]

KeyValueObject: TypeAlias = Union[
    ObjectLiteral, list["KeyValueObject"], dict[str, "KeyValueObject"]
]


def ensure_serialized(record: Union[DeserializableRecord, Deserializable]):
    if isinstance(record, dict):
        for val in record.values():
            if (
                val is not None
                and not isinstance(val, int)
                and not isinstance(val, float)
                and not isinstance(val, bool)
                and not isinstance(val, str)
            ):
                raise ValueError("Invalid value type, must be a primitive.")

    if (
        record is not None
        and not isinstance(record, int)
        and not isinstance(record, float)
        and not isinstance(record, bool)
        and not isinstance(record, str)
    ):
        raise ValueError("Invalid value type, must be a primitive.")


def deserialize_dates(
    record: Union[DeserializableRecord, SerializableRecord],
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


def serialize_dates(
    record: Union[SerializableRecord, Serializable, None],
) -> Union[DeserializableRecord, Deserializable, None]:
    if record is None:
        return None

    if isinstance(record, (date, time)):
        return record.isoformat()
    if isinstance(record, datetime):
        return isoformat_datetime(record)

    if isinstance(record, dict):
        return cast(
            DeserializableRecord,
            {key: serialize_dates(val) for key, val in record.items()},
        )

    return cast(Deserializable, record)


def format_datelike(d: Union[date, time, datetime]) -> str:
    if isinstance(d, datetime):
        return format_datetime(d)
    if isinstance(d, date):
        return format_date(d)
    if isinstance(d, time):
        return format_time(d)

    return str(d)


def format_date(d: date) -> str:
    return d.strftime("%x")


def format_time(t: time) -> str:
    return t.strftime("%X")


def format_datetime(d: datetime) -> str:
    return d.strftime("%c")


def isoformat_datetime(d: datetime) -> str:
    return d.isoformat(timespec="milliseconds") + "Z"
