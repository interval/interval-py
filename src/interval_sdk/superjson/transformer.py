import math, re
from datetime import date, time, datetime, timezone
from typing import Any, Callable, Union
from typing_extensions import TypeAlias, Literal

LeafTypeAnnotation: TypeAlias = Literal[
    "number", "Date", "regexp", "set", "map", "undefined"
]

CustomTypeAnnotation: TypeAlias = tuple[Literal["custom"], str]

CompositeTypeAnnotation: TypeAlias = CustomTypeAnnotation

TypeAnnotation: TypeAlias = Union[LeafTypeAnnotation, CompositeTypeAnnotation]

ISO_DATE_FORMAT_MICROSECONDS = "%Y-%m-%dT%H:%M:%S.%f%zZ"

REGEXP_FLAGS = {
    "i": re.I,
    "m": re.M,
}


class Undefined:
    pass


UNDEFINED = Undefined()


def transform_value(value: Any) -> Union[tuple[Any, TypeAnnotation], None]:
    if isinstance(value, Undefined):
        return (None, "undefined")
    if isinstance(value, float):
        if math.isinf(value):
            return ("Infinity", "number")
        if math.isnan(value):
            return ("NaN", "number")

    if isinstance(value, re.Pattern):
        flags = ""

        for flag_char, flag_const in REGEXP_FLAGS.items():
            if value.flags & flag_const:
                flags += flag_char

        return (f"/{value.pattern}/{flags}", "regexp")

    if isinstance(value, set):
        return (list(value), "set")

    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime(value.year, value.month, value.day)

    if isinstance(value, datetime):
        date_str = value.astimezone(tz=timezone.utc).isoformat(
            sep="T", timespec="milliseconds"
        )

        if "+" in date_str:
            date_str = date_str[: date_str.index("+")]

        return (
            date_str + "Z",
            "Date",
        )

    if isinstance(value, time):
        return (value.isoformat(), ("custom", "time"))

    return None


def untransform_value(value: Any, type: TypeAnnotation) -> Any:
    if isinstance(type, (tuple, list)):
        if type[0] == "custom":
            if type[1] == "time":
                [h, m, s] = [int(part) for part in str(value).split(":")]
                return time(h, m, s)

    if type == "number":
        return float(value)
    if type == "regexp":
        [pattern, flags_str] = str(value[1:]).split("/")
        flags = 0
        for c in flags_str:
            flags |= REGEXP_FLAGS.get(c, 0)
        return re.compile(pattern, flags)

    if type == "set":
        return set(value)

    if type == "map":
        return {key: val for [key, val] in value}

    if type == "Date":
        value = str(value)[:-1] + "000+00:00Z"
        d = (
            datetime.strptime(value, ISO_DATE_FORMAT_MICROSECONDS)
            .astimezone()
            .replace(tzinfo=None)
        )
        time_part = d.time()
        if time_part.hour == 0 and time_part.minute == 0 and time_part.second == 0:
            # if it looks like a timeless date we'll make it one
            return d.date()
        return d


def copy(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: copy(val) for key, val in obj.items()}
    if isinstance(obj, list):
        return [copy(val) for val in obj]
    if isinstance(obj, tuple):
        return tuple(*(copy(val) for val in obj))
    if isinstance(obj, set):
        return set(*(copy(val) for val in obj))
    return obj


def is_primitive(obj: Any) -> bool:
    return obj is None or isinstance(obj, (bool, int, float, str))


def is_deep(obj: Any) -> bool:
    return obj is not None and isinstance(obj, (list, dict, set, tuple))


def escape_key(key: str) -> str:
    return key.replace(".", "\\.")


def stringify_path(path: list[Union[str, int]]) -> str:
    return ".".join([str(v) for v in path])


def parse_path(path_str: str) -> list[str]:
    result: list[str] = []
    segment = ""
    i = 0
    while i < len(path_str):
        char = path_str[i]
        is_escaped_dot = char == "\\" and path_str[i + 1] == "."
        if is_escaped_dot:
            segment += "."
            i += 2
            continue

        is_end_of_segment = char == "."
        if is_end_of_segment:
            result.append(segment)
            segment = ""
            i += 1
            continue

        segment += char
        i += 1

    result.append(segment)

    return result


def validate_path(path: list[Union[str, int]]):
    for disallowed in ["__proto__", "prototype", "constructor"]:
        if disallowed in path:
            raise Exception(f"{disallowed} is not allowed as a property")


def get_nth_key(val: set, n: int) -> Union[Any, None]:
    for i, key in enumerate(val):
        if i == n:
            return key


def get_deep(obj: Any, path: list[Union[str, int]]) -> Any:
    validate_path(path)

    for key in path:
        if isinstance(obj, set):
            obj = get_nth_key(obj, int(key))
        elif isinstance(obj, list):
            obj = obj[int(key)]
        else:
            obj = obj[key]

    return obj


def set_deep(obj: Any, path: list[Union[str, int]], mapper: Callable[[Any], Any]):
    validate_path(path)

    if len(path) == 0:
        return mapper(obj)

    parent = obj
    for key in path[:-1]:
        if isinstance(parent, list):
            parent = parent[int(key)]
        else:
            parent = parent[key]

    last_key = path[-1]
    if isinstance(parent, set):
        old_value = get_nth_key(parent, int(last_key))
        new_value = mapper(old_value)
        if old_value != new_value:
            parent.remove(old_value)
            parent.add(new_value)
    else:
        if isinstance(parent, list):
            try:
                old_value = parent[int(last_key)]
            except IndexError:
                old_value = None
            parent[int(last_key)] = mapper(old_value)
        else:
            try:
                old_value = parent[last_key]
            except KeyError:
                old_value = None
            parent[last_key] = mapper(old_value)

    return obj
