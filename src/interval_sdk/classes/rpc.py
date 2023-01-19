import asyncio
from typing import Any, Callable, Generic, Optional

from typing_extensions import TypeVar, TypeAlias, Awaitable
from pydantic import ValidationError, parse_obj_as

from .logger import LogLevel, Logger
from ..internal_rpc_schema import AnyRPCSchemaMethodName, DuplexMessage, RPCMethod
from .isocket import ISocket
from ..util import dict_keys_to_camel

CallerSchemaMethodName = TypeVar("CallerSchemaMethodName", bound=AnyRPCSchemaMethodName)
ResponderSchemaMethodName = TypeVar(
    "ResponderSchemaMethodName", bound=AnyRPCSchemaMethodName
)

id_count = 0


def generate_id() -> str:
    global id_count  # pylint: disable=global-statement
    id_count += 1
    return str(id_count)


class DuplexRPCClient(Generic[CallerSchemaMethodName, ResponderSchemaMethodName]):
    # TODO: Try typing this
    RPCHandler: TypeAlias = Callable[[Any], Awaitable[Any]]

    _communicator: ISocket
    _can_call: dict[CallerSchemaMethodName, RPCMethod]
    _can_respond_to: dict[ResponderSchemaMethodName, RPCMethod]
    _handlers: dict[ResponderSchemaMethodName, RPCHandler]
    _pending_calls: dict[str, asyncio.Future[Any]]
    _logger: Logger

    def __init__(
        self,
        communicator: ISocket,
        can_call: dict[CallerSchemaMethodName, RPCMethod],
        can_respond_to: dict[ResponderSchemaMethodName, RPCMethod],
        handlers: dict[ResponderSchemaMethodName, RPCHandler],
        log_level: Optional[LogLevel] = None,
    ):
        self._communicator = communicator
        self._communicator.on_message = self._on_message
        self._can_call = can_call
        self._can_respond_to = can_respond_to
        self._handlers = handlers
        self._pending_calls = {}
        self._logger = Logger(log_level=log_level, prefix=self.__class__.__name__)

        self.set_communicator(communicator)

    def set_communicator(self, communicator: ISocket):
        if self._communicator is not None:
            self._communicator.on_message = None
        self._communicator = communicator
        self._communicator.on_message = self._on_message

    async def _on_message(self, data: str):
        try:
            input = DuplexMessage.parse_raw(data)

            if input.kind == "CALL":
                try:
                    return await self._handle_received_call(input)
                except (TimeoutError, asyncio.CancelledError) as err:
                    self._logger.debug(
                        "Call timed out:",
                        input,
                        err,
                    )
                    self._logger.print_exception(err)
                except KeyError as err:
                    self._logger.error(
                        "Received unsupported call:",
                        input,
                        err,
                    )
                    self._logger.print_exception(err)
                except ValidationError as err:
                    self._logger.error(
                        "Received invalid call:",
                        input,
                        err,
                    )
                    self._logger.print_exception(err)
                except Exception as err:
                    self._logger.error(
                        "Failed handling call:",
                        input,
                        err,
                    )
                    self._logger.print_exception(err)
            elif input.kind == "RESPONSE":
                try:
                    return await self._handle_received_response(input)
                except KeyError as err:
                    self._logger.error("Received unsupported response:", input, err)
                    self._logger.print_exception(err)
                except ValidationError as err:
                    self._logger.error("Received invalid response:", input, err)
                    self._logger.print_exception(err)
                except Exception as err:
                    self._logger.error("Failed handling response:", input, err)
                    self._logger.print_exception(err)

        except ValidationError:
            pass

    async def _handle_received_response(self, parsed: DuplexMessage):
        on_reply_fut = self._pending_calls.pop(parsed.id, None)
        if on_reply_fut is not None:
            on_reply_fut.set_result(parsed.data)

    async def _handle_received_call(
        self, parsed: DuplexMessage[ResponderSchemaMethodName]
    ):
        method_name = parsed.method_name
        method = self._can_respond_to[method_name]

        inputs = parse_obj_as(method.inputs, parsed.data)
        handler = self._handlers[method_name]
        return_value = await handler(inputs)

        message = DuplexMessage(
            id=parsed.id,
            method_name=method_name,
            data=return_value,
            kind="RESPONSE",
        )
        prepared_response_text = message.json()

        try:
            await self._communicator.send(prepared_response_text)
        except Exception as err:
            self._logger.error("Failed sending response", message, err)
            self._logger.print_exception(err)
            raise err

    async def send(self, method_name: CallerSchemaMethodName, inputs: dict[str, Any]):
        id = generate_id()

        message = DuplexMessage(
            id=id,
            data=dict_keys_to_camel(inputs),
            method_name=method_name,
            kind="CALL",
        )

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending_calls[id] = fut

        def handle_exceptions(task: asyncio.Task):
            try:
                task.result()
            except BaseException as err:
                self._logger.error("Error sending message", err)

        task = loop.create_task(self._communicator.send(message.json()), name="send")
        task.add_done_callback(handle_exceptions)

        raw_response_text = await fut
        parsed = parse_obj_as(self._can_call[method_name].returns, raw_response_text)

        return parsed
