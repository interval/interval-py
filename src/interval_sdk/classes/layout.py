from dataclasses import dataclass
from typing import Optional

from typing_extensions import Literal, TypeAlias

from pydantic import Field

from ..classes.io_promise import DisplayIOPromise
from ..types import BaseModel
from ..io_schema import ButtonItem, ButtonItemModel, IORender
from ..util import Eventual

PageLayoutKey = Literal["title", "description", "children", "menuItems"]


class PageError(BaseModel):
    layout_key: PageLayoutKey
    error: str
    message: str
    cause: Optional[str] = None
    stack: Optional[str] = None


EventualStr: TypeAlias = Eventual[str]


@dataclass
class BasicLayout:
    kind: Literal["BASIC"] = "BASIC"
    title: Optional[EventualStr] = None
    description: Optional[EventualStr] = None
    children: Optional[list[DisplayIOPromise]] = None
    menu_items: Optional[list[ButtonItem]] = None


Layout: TypeAlias = BasicLayout


class BasicLayoutModel(BaseModel):
    kind: Literal["BASIC"]
    title: Optional[str] = None
    description: Optional[str] = None
    children: Optional[IORender] = None
    menu_items: Optional[list[ButtonItemModel]] = None
    errors: list[PageError] = Field(default_factory=list)
