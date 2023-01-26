from typing import Any, Optional, TypedDict
from typing_extensions import NotRequired

from .transformer import TypeAnnotation, copy

from .plainer import MinimizedTree, apply_value_annotations, walker


class SuperJSONMeta(TypedDict):
    values: NotRequired[MinimizedTree[TypeAnnotation]]


SuperJSONResult = tuple[Any, Optional[SuperJSONMeta]]


def serialize(obj: Any) -> SuperJSONResult:
    """
    This only handles a subset of types that we currently care about, and no referential equality.
    """
    (transformed_value, annotations) = walker(obj, {})

    meta: Optional[SuperJSONMeta] = None
    if annotations is not None:
        meta = {
            "values": annotations,
        }

    return (transformed_value, meta)


def deserialize(json: Any, meta: Optional[SuperJSONMeta] = None) -> Any:
    """
    This only handles a subset of types that we currently care about, and no referential equality.
    """
    result = copy(json)
    if meta is not None and "values" in meta:
        result = apply_value_annotations(result, meta["values"])

    return result
