import json
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

from typing_extensions import Literal, TypeAlias, Awaitable

from pydantic import Field

from ..classes.io_promise import DisplayIOPromise
from ..types import BaseModel
from ..io_schema import ButtonItem, ButtonItemModel, IORender, dump_io_render
from ..util import dump_snake_obj, json_loads_camel, snake_to_camel

PageLayoutKey = Literal["title", "description", "children", "menuItems"]


class PageError(BaseModel):
    layout_key: PageLayoutKey
    error: str
    message: str
    cause: Optional[str] = None
    stack: Optional[str] = None


EventualStr: TypeAlias = Union[str, Awaitable[str], Callable[[], Awaitable[str]]]


@dataclass
class BasicLayout:
    kind: Literal["BASIC"] = "BASIC"
    title: Optional[EventualStr] = None
    description: Optional[EventualStr] = None
    children: Optional[list[DisplayIOPromise]] = None
    menu_items: Optional[list[ButtonItem]] = None


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
    title: Optional[str] = None
    description: Optional[str] = None
    children: Optional[IORender] = None
    menu_items: Optional[list[ButtonItemModel]] = None
    errors: list[PageError] = Field(default_factory=list)

    class Config:
        json_dumps = json_dumps_basic_layout_model
        json_loads = json_loads_camel
