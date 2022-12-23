from typing import TypeAlias, Awaitable, Callable

from .io_schema import IOFunctionReturnType
from .internal_rpc_schema import ActionContext, PageContext
from .classes.io import IO
from .classes.io_client import IOResponse
from .classes.layout import Layout

IntervalActionHandler: TypeAlias = (
    Callable[[], Awaitable[IOFunctionReturnType]]
    | Callable[[IO], Awaitable[IOFunctionReturnType]]
    | Callable[[IO, ActionContext], Awaitable[IOFunctionReturnType]]
)

IntervalPageHandler: TypeAlias = (
    Callable[[], Awaitable[Layout]]
    | Callable[[IO.Display], Awaitable[Layout]]
    | Callable[[IO.Display, PageContext], Awaitable[Layout]]
)

IOResponseHandler: TypeAlias = Callable[[IOResponse], Awaitable[None]]
