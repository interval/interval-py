import json
from dataclasses import dataclass
from typing import Any, Callable, Literal, Awaitable, TypeAlias

from interval_sdk.classes.io_promise import DisplayIOPromise
from interval_sdk.util import dump_snake_obj, json_loads_camel, snake_to_camel

from ..types import BaseModel
from ..io_schema import ButtonItem, ButtonItemModel, IORender, dump_io_render

PageLayoutKey = Literal["title", "description", "children", "menuItems"]


class PageError(BaseModel):
    layout_key: PageLayoutKey
    error: str
    message: str
    cause: str | None = None
    stack: str | None = None


EventualStr: TypeAlias = str | Awaitable[str] | Callable[[], Awaitable[str]]


@dataclass
class BasicLayout:
    kind: Literal["BASIC"] = "BASIC"
    title: EventualStr | None = None
    description: EventualStr | None = None
    children: list[DisplayIOPromise] | None = None
    menu_items: list[ButtonItem] | None = None


Layout: TypeAlias = BasicLayout


def json_dumps_basic_layout_model(layout: dict[str, Any], *args, **kwargs) -> str:
    obj = {}
    for key, val in layout.items():
        if key == "children":
            obj[snake_to_camel(key)] = dump_io_render(val)
        else:
            obj[snake_to_camel(key)] = dump_snake_obj(val)

    return json.dumps(obj, *args, **kwargs)


class BasicLayoutModel(BaseModel):
    kind: Literal["BASIC"]
    title: str | None = None
    description: str | None = None
    children: IORender | None = None
    menu_items: list[ButtonItemModel] | None = None
    errors: list[PageError] = []

    class Config:
        json_dumps = json_dumps_basic_layout_model
        json_loads = json_loads_camel
