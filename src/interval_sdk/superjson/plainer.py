from typing import Any, Callable, Iterable, TypeVar, Union
from typing_extensions import TypeAlias

from .transformer import (
    TypeAnnotation,
    escape_key,
    is_deep,
    is_primitive,
    parse_path,
    set_deep,
    transform_value,
    untransform_value,
)

T = TypeVar("T")

Leaf: TypeAlias = tuple[T]
InnerNode: TypeAlias = tuple[T, dict[str, "Tree[T]"]]
Tree: TypeAlias = Union[InnerNode[T], Leaf[T]]

MinimizedTree: TypeAlias = Union[Tree[T], dict[str, Tree[T]], None]
Identities: TypeAlias = dict[Any, list[list[Any]]]

WalkResult: TypeAlias = tuple[Any, Union[MinimizedTree[TypeAnnotation], None]]


def traverse(
    tree: MinimizedTree[T],
    walker: Callable[[T, list[Union[str, int]]], None],
    origin: list[Union[str, int]] = [],
):
    if tree is None:
        return

    if isinstance(tree, dict):
        for key, subtree in tree.items():
            traverse(subtree, walker, [*origin, *parse_path(key)])
        return

    if isinstance(tree, (tuple, list)):
        if len(tree) == 2:
            [node_value, children] = tree
            for key, child in children.items():
                traverse(child, walker, [*origin, *parse_path(key)])
        else:
            [node_value] = tree

        walker(node_value, origin)


def apply_value_annotations(plain: Any, annotations: MinimizedTree[TypeAnnotation]):
    def walker(type: TypeAnnotation, path: list[Union[str, int]]):
        nonlocal plain
        plain = set_deep(plain, path, lambda v: untransform_value(v, type))

    traverse(annotations, walker)

    return plain


def add_identity(obj: Any, path: list[Any], identities: Identities):
    try:
        identities[obj].append(path)
    except KeyError:
        identities[obj] = [path]


def walker(
    obj: Any,
    identities: Identities,
    path: list[Any] = [],
    objects_in_this_path: list[Any] = [],
) -> WalkResult:
    # if not is_primitive(obj):
    #     add_identity(obj=obj, path=path, identities=identities)

    if not is_deep(obj):
        transformed = transform_value(obj)
        if transformed is not None:
            return (transformed[0], (transformed[1],))
        return (obj, None)

    if obj in objects_in_this_path:
        return (None, None)

    transformation_result = transform_value(obj)
    transformed = transformation_result[0] if transformation_result is not None else obj

    if not is_primitive(obj):
        objects_in_this_path = [*objects_in_this_path, obj]

    transformed_value = [] if isinstance(transformed, list) else {}
    inner_annotations: dict[str, Tree[TypeAnnotation]] = {}

    kvs: Iterable
    if isinstance(transformed, dict):
        kvs = transformed.items()
    else:
        kvs = enumerate(transformed)

    for index, value in kvs:
        recursive_result = walker(
            value, identities, [*path, index], objects_in_this_path
        )
        try:
            transformed_value[index] = recursive_result[0]
        except IndexError:
            if isinstance(transformed_value, list):
                transformed_value.append(recursive_result[0])
        if len(recursive_result) > 1:
            if isinstance(recursive_result[1], (tuple, list)):
                inner_annotations[str(index)] = recursive_result[1]
            elif isinstance(recursive_result[1], dict):
                for key, tree in recursive_result[1].items():
                    inner_annotations[f"{escape_key(str(index))}.{key}"] = tree

    if len(inner_annotations) == 0:
        return (
            transformed_value,
            (transformation_result[1],) if transformation_result is not None else None,
        )

    return (
        transformed_value,
        (transformation_result[1], inner_annotations)
        if transformation_result is not None
        else inner_annotations,
    )
