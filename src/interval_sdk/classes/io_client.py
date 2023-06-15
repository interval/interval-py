import asyncio
import inspect
from typing import Optional, cast, Callable
from uuid import UUID, uuid4

from typing_extensions import TypeAlias, TypeVar, Any, Awaitable

from .. import superjson
from ..io_schema import (
    ChoiceButtonConfig,
    ChoiceReturn,
    MethodName,
    IORender,
    IOResponse,
)
from .component import Component, WithChoicesIOGroupPromiseValidator
from .io_error import IOError
from .io import IO
from .logger import Logger


MN = TypeVar("MN", bound=MethodName)


class IOClient:
    Sender: TypeAlias = Callable[[IORender], Awaitable[None]]
    _logger: Logger
    _send: Sender
    _on_response_handlers: dict[UUID, Callable[[IOResponse], Awaitable[None]]]
    _previous_input_group_key: Optional[UUID] = None

    _is_canceled = False

    def __init__(
        self,
        logger: Logger,
        send: Sender,
        *,
        display_resolves_immediately: Optional[bool] = None,
    ):
        self._logger = logger
        self._send = send
        self._on_response_handlers = {}

        self.io = IO(
            self.render_components,
            logger=logger,
            display_resolves_immediately=display_resolves_immediately,
        )

    @property
    def is_canceled(self) -> bool:
        return self._is_canceled

    async def on_response(self, response: IOResponse):
        input_group_key = (
            response.input_group_key
            if response.input_group_key is not None
            else self._previous_input_group_key
        )

        if input_group_key is None or input_group_key == "UNKNOWN":
            self._logger.error("Received response without an input group key")
            return

        try:

            input_group_handler = self._on_response_handlers[input_group_key]

            if input_group_handler is not None:
                try:
                    await input_group_handler(response)
                except Exception as err:
                    self._logger.error("Error in input group response handler:", err)
                    self._logger.print_exception(err)
        except KeyError:
            self._logger.error(
                "No response handler defined for input group key", input_group_key
            )

    async def render_components(
        self,
        components: list[Component],
        group_validator: Optional[WithChoicesIOGroupPromiseValidator] = None,
        choice_buttons: Optional[list[ChoiceButtonConfig]] = None,
    ) -> tuple[list[Any], Optional[str]]:
        if self._is_canceled:
            raise IOError("TRANSACTION_CLOSED")

        validation_error_message: Optional[str] = None

        input_group_key = uuid4()
        is_returned = False

        loop = asyncio.get_running_loop()
        choice_future = loop.create_future()

        async def render():
            packed = IORender(
                id=uuid4(),
                input_group_key=input_group_key,
                to_render=[inst.render_info for inst in components],
                kind="RENDER",
                validation_error_message=validation_error_message,
                choice_buttons=choice_buttons,
            )

            await self._send(packed)

        def handle_render_error(task: asyncio.Task):
            try:
                task.result()
            except BaseException as err:
                choice_future.set_exception(err)
                for component in components:
                    component.set_exception(err)
                return

        async def on_response_handler(response: IOResponse):
            nonlocal validation_error_message, is_returned
            if response.input_group_key != input_group_key:
                self._logger.debug("Received response for other input group")
                return

            if (self._is_canceled or is_returned) and (
                response.kind == "RETURN" or response.kind == "CANCELED"
            ):
                self._logger.debug("Received response after IO call complete")
                return

            if response.kind == "CANCELED":
                self._is_canceled = True
                err = IOError("CANCELED")
                choice_future.set_exception(err)
                for component in components:
                    component.set_exception(err)
                return

            if len(response.values) != len(components):
                raise Exception("Mismatch in return array length")

            if response.values_meta is not None:
                response.values = superjson.deserialize(
                    response.values, response.values_meta
                )

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
                    task.add_done_callback(handle_render_error)
                    return

                if group_validator is not None:
                    # we check that these are valid above, if any are invalid we wouldn't make it this far
                    parsed_values = [
                        components[i].parse_return_value(val)
                        for i, val in enumerate(response.values)
                    ]
                    resp = group_validator(
                        ChoiceReturn(
                            choice=cast(str, response.choice),
                            return_value=cast(tuple[Any], parsed_values),
                        )
                    )
                    validation_error_message = cast(
                        Optional[str], await resp if inspect.isawaitable(resp) else resp
                    )

                    if validation_error_message is not None:
                        task = loop.create_task(render())
                        task.add_done_callback(handle_render_error)
                        return

                is_returned = True
                choice_future.set_result(response.choice)

                for i, value in enumerate(response.values):
                    components[i].set_return_value(value)
                return

            if response.kind == "SET_STATE":
                for index, new_state in enumerate(response.values):
                    prev_state = components[index].instance.state

                    if new_state is not None and new_state != prev_state:
                        try:
                            await components[index].set_state(new_state)
                        except BaseException as err:
                            self._logger.error(
                                f"Error updating {components[index].instance.method_name} component state, ignoring state update:"
                            )
                            self._logger.print_exception(err)

                task = loop.create_task(render())
                task.add_done_callback(handle_render_error)

        self._on_response_handlers[input_group_key] = on_response_handler
        self._previous_input_group_key = input_group_key

        for c in components:
            c.on_state_change = render

        def resolve_immediates(t: asyncio.Task):
            try:
                t.result()
                all_resolved = True
                for c in components:
                    if c.resolves_immediately:
                        c.set_return_value(None)
                    else:
                        all_resolved = False

                if (
                    all_resolved
                    and not choice_future.done()
                    and (choice_buttons is None or len(choice_buttons) == 0)
                ):
                    choice_future.set_result(None)

            except Exception as err:
                for c in components:
                    c.set_exception(err)
                choice_future.set_exception(err)

        # initial render
        task = loop.create_task(render())
        task.add_done_callback(resolve_immediates)

        return_futures = [component.return_value for component in components]

        # Actually does return a list, just says Tuple for variadic type
        # https://github.com/python/typeshed/blob/4d23919200d9e89486f4d9e2587f82314d4af0f6/stdlib/asyncio/tasks.pyi#L82-L85
        return (
            cast(list[Any], await asyncio.gather(*return_futures)),
            cast(Optional[str], await choice_future),
        )
