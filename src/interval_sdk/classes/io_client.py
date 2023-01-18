import asyncio
import inspect
from typing import Optional, cast, Callable
from uuid import uuid4

from typing_extensions import TypeAlias, TypeVar, Any, Awaitable

from pydantic import parse_obj_as

from ..io_schema import ButtonConfig, MethodName, IORender, IOResponse
from .component import Component, IOPromiseValidator
from .io_error import IOError
from .io import IO
from .logger import Logger


MN = TypeVar("MN", bound=MethodName)


class IOClient:
    Sender: TypeAlias = Callable[[IORender], Awaitable[None]]
    _logger: Logger
    _send: Sender
    _on_response_handler: Optional[Callable[[IOResponse], Awaitable[None]]] = None

    _is_canceled = False

    def __init__(self, logger: Logger, send: Sender):
        self._logger = logger
        self._send = send

        self.io = IO(self.render_components)

    @property
    def is_canceled(self) -> bool:
        return self._is_canceled

    async def on_response(self, response: IOResponse):
        if self._on_response_handler is not None:
            try:
                await self._on_response_handler(response)
            except Exception as err:
                self._logger.error("Error in on_response_handler:", err)
                self._logger.print_exception(err)

    async def render_components(
        self,
        components: list[Component],
        group_validator: Optional[IOPromiseValidator] = None,
        continue_button: Optional[ButtonConfig] = None,
    ) -> list[Any]:
        if self._is_canceled:
            raise IOError("TRANSACTION_CLOSED")

        validation_error_message: Optional[str] = None

        input_group_key = uuid4()
        is_returned = False

        async def render():
            packed = IORender(
                id=uuid4(),
                input_group_key=input_group_key,
                to_render=[inst.render_info for inst in components],
                kind="RENDER",
                validation_error_message=validation_error_message,
                continue_button=continue_button,
            )

            await self._send(packed)

        loop = asyncio.get_running_loop()
        fut = loop.create_future()

        async def on_response_handler(response: IOResponse):
            nonlocal validation_error_message, is_returned
            if response.input_group_key != str(input_group_key):
                self._logger.debug("Received response for other input group")
                return

            if self._is_canceled or is_returned:
                self._logger.debug("Received response after IO call complete")
                return

            if response.kind == "CANCELED":
                self._is_canceled = True
                fut.set_exception(IOError("CANCELED"))
                return

            if len(response.values) != len(components):
                raise Exception("Mismatch in return array length")

            if response.kind == "RETURN":

                async def check_invalidity(index: int, value: Any) -> bool:
                    """Returns True if invalid, False if valid"""
                    component = components[index]
                    resp = await component.handle_validation(value)
                    return resp is not None

                invalidities: list[bool] = await asyncio.gather(
                    *(
                        check_invalidity(i, value)
                        for i, value in enumerate(response.values)
                    )
                )

                validation_error_message = None

                if any(invalidities):
                    task = loop.create_task(render())
                    task.add_done_callback(self._logger.handle_task_exceptions)
                    return

                if group_validator is not None:
                    # we check that these are valid above, if any are invalid we wouldn't make it this far
                    parsed_values = [
                        components[i].parse_return_value(val)
                        for i, val in enumerate(response.values)
                    ]
                    resp = group_validator(parsed_values)
                    validation_error_message = cast(
                        Optional[str], await resp if inspect.isawaitable(resp) else resp
                    )

                    if validation_error_message is not None:
                        task = loop.create_task(render())
                        task.add_done_callback(self._logger.handle_task_exceptions)
                        return

                is_returned = True

                for i, value in enumerate(response.values):
                    components[i].set_return_value(value)
                return

            if response.kind == "SET_STATE":
                for index, new_state in enumerate(response.values):
                    prev_state = components[index].instance.state

                    if new_state != prev_state:
                        await components[index].set_state(new_state)
                task = loop.create_task(render())
                task.add_done_callback(self._logger.handle_task_exceptions)

        self._on_response_handler = on_response_handler

        for c in components:
            c.on_state_change = render

        # initial render
        task = loop.create_task(render())
        task.add_done_callback(self._logger.handle_task_exceptions)

        return_futures = [component.return_value for component in components]

        # Actually does return a list, just says Tuple for variadic type
        # https://github.com/python/typeshed/blob/4d23919200d9e89486f4d9e2587f82314d4af0f6/stdlib/asyncio/tasks.pyi#L82-L85
        return cast(list[Any], await asyncio.gather(*return_futures))
