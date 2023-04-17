from typing import Awaitable, Callable, Union
from typing_extensions import TypeAlias

from .io_schema import IOFunctionReturnType
from .internal_rpc_schema import ActionContext, PageContext
from .classes.io import IO
from .classes.io_client import IOResponse
from .classes.layout import Layout

IntervalActionHandler: TypeAlias = Union[
    Callable[[], Awaitable[IOFunctionReturnType]],
    Callable[[IO], Awaitable[IOFunctionReturnType]],
    Callable[[IO, ActionContext], Awaitable[IOFunctionReturnType]],
]

IntervalPageHandler: TypeAlias = Union[
    Callable[[], Awaitable[Union[Layout, None]]],
    Callable[[IO.Display], Awaitable[Union[Layout, None]]],
    Callable[[IO.Display, PageContext], Awaitable[Union[Layout, None]]],
]

IOResponseHandler: TypeAlias = Callable[[IOResponse], Awaitable[None]]
