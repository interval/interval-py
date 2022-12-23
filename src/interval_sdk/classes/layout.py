from typing import Literal, Awaitable, TypeAlias
from uuid import uuid4

from pydantic.dataclasses import dataclass

from interval_sdk.classes.io_promise import DisplayIOPromise
from interval_sdk.util import json_dumps_snake, json_loads_camel

from ..types import BaseModel
from ..io_schema import ButtonItem, ButtonItemModel, IORender


class PageError(BaseModel):
    layout_key: Literal["title", "description", "children", "menuItems"]
    error: str
    message: str
    cause: str | None = None
    stack: str | None = None


EventualStr: TypeAlias = str | Awaitable[str]


@dataclass
class BasicLayout:
    title: EventualStr | None = None
    description: EventualStr | None = None
    children: list[DisplayIOPromise] | None = None
    menu_items: list[ButtonItem] | None = None


Layout = BasicLayout


class BasicLayoutModel(BaseModel):
    title: str | None = None
    description: str | None = None
    children: IORender | None = None
    menu_items: list[ButtonItemModel] | None = None
    errors: list[PageError] = []

    class Config:
        json_dumps = json_dumps_snake
        json_loads = json_loads_camel
