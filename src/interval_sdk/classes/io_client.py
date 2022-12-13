import asyncio
from typing import cast, Awaitable, TypeAlias, Callable, TypeVar, Any
from uuid import uuid4

from ..io_schema import *
from .component import Component
from .io_error import IOError
from .io import IO
from .logger import Logger


MN = TypeVar("MN", bound=MethodName)


class IOClient:
    Sender: TypeAlias = Callable[[IORender], Awaitable[None]]
    _logger: Logger
    _send: Sender
    _on_response_handler: Callable[[IOResponse], Awaitable[None]]

    _is_canceled = False

    def __init__(self, logger: Logger, send: Sender):
        self._logger = logger
        self._send = send

        self.io = IO(self.render_components)

    @property
    def is_canceled(self) -> bool:
        return self._is_canceled

    async def on_response(self, response: IOResponse):
        if self._on_response_handler:
            try:
                await self._on_response_handler(response)
            except Exception as err:
                self._logger.error("Error in on_response_handler:", err)
                self._logger.print_exception(err)

    async def render_components(self, components: list[Component]) -> list[Any]:
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

        loop = asyncio.get_running_loop()
        fut = loop.create_future()

        async def on_response_handler(response: IOResponse):
            if response.kind == "CANCELED":
                self._is_canceled = True
                fut.set_exception(IOError("CANCELED"))
                return

            if len(response.values) != len(components):
                raise Exception("Mismatch in return array length")

            if response.kind == "RETURN":
                for i, value in enumerate(response.values):
                    components[i].set_return_value(value)
                return

            elif response.kind == "SET_STATE":
                for index, new_state in enumerate(response.values):
                    prev_state = components[index].instance.state

                    if new_state != prev_state:
                        await components[index].set_state(new_state)
                asyncio.create_task(render())

        self._on_response_handler = on_response_handler

        for c in components:
            if c.on_state_change:
                c.on_state_change = render

        # initial render
        asyncio.create_task(render())

        return_futures = [component.return_value for component in components]

        # Actually does return a list, just says Tuple for variadic type
        # https://github.com/python/typeshed/blob/4d23919200d9e89486f4d9e2587f82314d4af0f6/stdlib/asyncio/tasks.pyi#L82-L85
        return cast(list[Any], await asyncio.gather(*return_futures))
