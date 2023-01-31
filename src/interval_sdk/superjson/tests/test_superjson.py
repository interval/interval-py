import math, json, re, subprocess
from pathlib import Path
from datetime import date, time, datetime
import sys
from typing import Any, Callable
from typing_extensions import TypeAlias

from .. import serialize, deserialize

EqualityChecker: TypeAlias = Callable[[Any, Any], bool]


def is_eq(a: Any, b: Any) -> bool:
    return a == b


def test_basic():
    round_trip_all(
        [
            1,
            1.234,
            "a",
            {"a": "b", "c": ["d", 1], "e": {"f": "g"}},
            [1, 2, 3],
        ]
    )


def test_numbers():
    round_trip_all([math.inf, math.inf])
    round_trip_all(math.nan, lambda a, b: math.isnan(a) and math.isnan(b))


def test_dates():
    round_trip_all(
        {"date": date(1993, 11, 12), "datetime": datetime(2000, 1, 2, 3, 4, 5)}
    )


def test_time():
    o = [time(11, 11, 11)]
    round_trip_all(o)


def test_regexp():
    round_trip_all(re.compile("abcd\\w.", re.I))


def test_set():
    round_trip_all([{1, 2, 3}])


def test_map():
    node_script_path = Path(__file__).parent / "node-only-types.js"
    received_from_node = None
    with subprocess.Popen(
        ["node", node_script_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        if process.stdout is not None:
            received_from_node = process.stdout.read().decode("utf-8")

        process.wait()

    assert received_from_node is not None

    print(received_from_node)

    parsed = json.loads(received_from_node)

    out = deserialize(parsed["json"], parsed.get("meta", None))

    assert out["map"] == {1: 2, "a": "b"}


def round_trip_all(start: Any, equality_checker: EqualityChecker = is_eq):
    round_trip(start, equality_checker)
    json_round_trip(start, equality_checker)
    node_round_trip(start, equality_checker)


def round_trip(start: Any, equality_checker: EqualityChecker = is_eq):
    data, meta = serialize(start)
    print(data, meta)
    out = deserialize(data, meta)

    print(start, out)
    assert equality_checker(start, out)


def json_round_trip(start: Any, equality_checker: EqualityChecker = is_eq):
    data, meta = serialize(start)
    data_s = json.dumps(data)
    meta_s = json.dumps(meta)

    data_r = json.loads(data_s)
    meta_r = json.loads(meta_s)

    print(data, data_r)
    print(meta, meta_r)

    out = deserialize(data_r, meta_r)

    print(start, out)
    assert equality_checker(start, out)


def node_round_trip(start: Any, equality_checker: EqualityChecker = is_eq):
    data, meta = serialize(start)
    s = json.dumps({"json": data, "meta": meta})
    node_script_path = Path(__file__).parent / "round-trip-superjson.js"
    received_from_node = None
    with subprocess.Popen(
        ["node", node_script_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
    ) as process:
        if process.stdin is not None:
            process.stdin.write(s.encode("utf-8"))
            process.stdin.close()
        if process.stdout is not None:
            received_from_node = process.stdout.read().decode("utf-8")

        process.wait()

    assert received_from_node is not None

    reparsed = json.loads(received_from_node)
    print(reparsed)

    out = deserialize(reparsed["json"], reparsed.get("meta", None))
    print(out)

    assert equality_checker(start, out)
