import asyncio
from asyncio import Future
import traceback
from typing import Any, Callable, Generic, TypeVar, TypeAlias, Awaitable

from pydantic import parse_obj_as

from .internal_rpc_schema import DuplexMessage, MethodDef
from .isocket import ISocket
from .types import BaseModel, dict_keys_to_camel

# I think this is right? or covariant=
CallerSchema = TypeVar("CallerSchema", bound=MethodDef)
ResponderSchema = TypeVar("ResponderSchema", bound=MethodDef)

id_count = 0


def generate_id():
    global id_count
    id_count += 1
    return str(id_count)


class DuplexRPCClient(Generic[CallerSchema, ResponderSchema]):
    # TODO: Try typing this
    RPCHandler: TypeAlias = Callable[[Any], Awaitable[Any]]

    _communicator: ISocket
    _can_call: CallerSchema
    _can_respond_to: ResponderSchema
    _handlers: dict[str, RPCHandler] = {}
    _pending_calls: dict[str, Future[Any]] = {}

    def __init__(
        self,
        communicator: ISocket,
        can_call: CallerSchema,
        can_respond_to: ResponderSchema,
        handlers: dict[str, RPCHandler],
    ):
        self._communicator = communicator
        self._communicator.on_message = self._on_message
        self._can_call = can_call
        self._can_respond_to = can_respond_to
        self._handlers = handlers

        self.set_communicator(communicator)

    def set_communicator(self, communicator: ISocket):
        if self._communicator is not None:
            self._communicator.on_message = None
        self._communicator = communicator
        self._communicator.on_message = self._on_message

    async def _on_message(self, data: str):
        input = DuplexMessage.parse_raw(data)

        if input.kind == "RESPONSE":
            return await self._handle_received_response(input)
        elif input.kind == "CALL":
            return await self._handle_received_call(input)

    async def _handle_received_response(self, parsed: DuplexMessage):
        on_reply_fut = self._pending_calls.pop(parsed.id, None)
        if on_reply_fut is not None:
            on_reply_fut.set_result(parsed.data)

    async def _handle_received_call(self, parsed: DuplexMessage):
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

        await self._communicator.send(prepared_response_text)

    # TODO: Can this be typed?
    async def send(self, method_name: str, inputs: BaseModel):
        id = generate_id()

        message = DuplexMessage(
            id=id,
            data=dict_keys_to_camel(inputs.dict()),
            method_name=method_name,
            kind="CALL",
        )

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending_calls[id] = fut

        asyncio.create_task(self._communicator.send(message.json()), name="send")

        try:
            raw_response_text = await fut
            parsed = parse_obj_as(
                self._can_call[method_name].returns, raw_response_text
            )

            return parsed
        except Exception as err:
            traceback.print_exception(err)

        return None
