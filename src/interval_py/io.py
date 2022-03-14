import asyncio, sys
from asyncio.futures import Future
from dataclasses import dataclass
from typing import Awaitable, TypeAlias, Callable, Literal, TypeVar, Generic, Any
from uuid import uuid4

from .io_schema import IORender, MethodName, IOResponse
from .component import Component

IOErrorKind = Literal["CANCELED", "TRANSACTION_CLOSED"]


class IOError(Exception):
    kind: IOErrorKind
    message: str | None

    def __init__(self, kind: IOErrorKind, message: str | None = None):
        super()
        self.kind = kind
        self.message = message


MN = TypeVar("MN", bound=MethodName)

LogLevel: TypeAlias = Literal["prod", "debug"]


class Logger:
    log_level: LogLevel = "prod"

    def __init__(self, log_level: LogLevel = "prod"):
        self.log_level = log_level

    def prod(self, *kwargs):
        print("[Interval]", *kwargs)

    def warn(self, *kwargs):
        print(*kwargs, file=sys.stderr)

    def error(self, *kwargs):
        print(*kwargs, file=sys.stderr)

    def debug(self, **kwargs):
        if self.log_level == "debug":
            print(**kwargs)


# TODO: Exclusive / groupable
# TODO: Separate type for Optional
class IOPromise(Generic[MN]):
    component: Component
    optional: bool

    def __init__(self, component: Component, optional=False):
        self.component = component
        self.optional = optional

    async def __await__(self):
        yield None


class IOClient:
    Sender: TypeAlias = Callable[[IORender], Awaitable[None]]
    _logger: Logger
    _send: Sender
    _on_response_handler: Callable[[IOResponse], Awaitable[None]]

    _is_canceled = False

    def __init__(self, logger: Logger, send: Sender):
        self._logger = logger
        self._send = send

    @property
    def is_canceled(self):
        return self._is_canceled

    async def on_response(self, response: IOResponse):
        if self._on_response_handler:
            try:
                self._on_response_handler(response)
            except Exception as err:
                self._logger.error("Error in on_response_handler:", err)

    async def render_components(self, components: list[Component]):
        if self._is_canceled:
            raise IOError("TRANSACTION_CLOSED")

        input_group_key = uuid4()

        async def render():
            packed = IORender(
                id=uuid4(),
                input_group_key=input_group_key,
                to_render=[inst.render_info for inst in components],
                kind="RENDER",
            )

            await self._send(packed)

        loop = asyncio.get_event_loop()
        fut = loop.create_future()

        async def on_response_handler():
            pass

    async def group(self, io_promises: list[IOPromise]):
        pass

    class IO:
        pass

        class Input:
            pass

        class Select:
            pass

        class Display:
            pass

        class Experimental:
            pass

            class Progress:
                pass
