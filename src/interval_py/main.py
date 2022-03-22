import asyncio
from inspect import signature
from typing import Optional, TypeAlias, Callable, Awaitable
from uuid import uuid4, UUID

import websockets, websockets.client, websockets.exceptions

from .isocket import ISocket
from .io_schema import ActionResult, IOFunctionReturnType
from .io_client import IOClient, Logger, LogLevel, IOError
from .io import IO, IOResponse, IORender
from .rpc import DuplexRPCClient
from .internal_rpc_schema import *
from .util import serialize_dates, deserialize_dates


IntervalActionHandler: TypeAlias = (
    Callable[[], Awaitable[IOFunctionReturnType]]
    | Callable[[IO], Awaitable[IOFunctionReturnType]]
    | Callable[[IO, ActionContext], Awaitable[IOFunctionReturnType]]
)

IOResponseHandler: TypeAlias = Callable[[IOResponse], Awaitable[None]]


class Interval:
    _logger: Logger
    _endpoint: str = "wss://intervalkit.com/websocket"
    _api_key: str
    _actions: dict[str, IntervalActionHandler]

    _io_response_handlers: dict[str, IOResponseHandler] = {}
    _isocket: ISocket | None = None
    _server_rpc: DuplexRPCClient[WSServerSchema, HostSchema] | None = None
    _is_connected: bool = False

    def __init__(
        self, api_key: str, endpoint: Optional[str] = None, log_level: LogLevel = "prod"
    ):
        self._api_key = api_key
        if endpoint is not None:
            self._endpoint = endpoint

        self._actions = {}
        self._logger = Logger(log_level)

    def action(self, action_callback: IntervalActionHandler) -> None:
        return self._add_action(action_callback.__name__, action_callback)

    def action_with_slug(self, slug: str) -> Callable[[IntervalActionHandler], None]:
        def action_adder(action_callback: IntervalActionHandler):
            self._add_action(slug, action_callback)

        return action_adder

    def enqueue(self, slug: str):
        pass
        # TODO

    def dequeue(self, id: str):
        pass
        # TODO

    @property
    def _log(self):
        return self._logger

    def _add_action(self, slug: str, action_callback: IntervalActionHandler) -> None:
        self._actions[slug] = action_callback

    @property
    def is_connected(self):
        return self._is_connected

    def listen(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.listen_async())
        loop.run_forever()

    async def listen_async(self):
        await self._create_socket_connection()
        self._create_rpc_client()
        await self._initialize_host()

    async def _create_socket_connection(self, instance_id: UUID = uuid4()):
        async def on_close(code: int, reason: str):
            if not self._is_connected:
                return

            self._log.prod(
                f"Lost connection to Interval (code {code}). Reason: {reason}"
            )
            self._log.prod("Reconnecting...")

            self._is_connected = False

            def on_reconnect(_):
                self._log.prod("Reconnection successful")
                self._is_connected = True

            while not self._is_connected:
                task = asyncio.create_task(
                    self._create_socket_connection(instance_id=instance_id)
                )
                task.add_done_callback(on_reconnect)

                self._log.prod("Unable to reconnect. Retrying in 3s...")
                await asyncio.sleep(3)

        ws = await websockets.client.connect(
            self._endpoint,
            extra_headers={
                "x-api-key": self._api_key,
                "x-instance-id": str(instance_id),
            },
            open_timeout=10,
        )

        self._isocket = ISocket(
            id=instance_id,
            ws=ws,
            on_close=on_close,
        )

        await self._isocket.connect()
        self._is_connected = True

        if self._server_rpc is None:
            return

        self._server_rpc.set_communicator(self._isocket)
        await self._initialize_host()

    def _create_rpc_client(self):
        if self._isocket is None:
            raise Exception("ISocket not initialized")

        async def start_transaction(inputs: StartTransactionInputs):
            slug = inputs.action_name
            handler = self._actions.get(slug, None)

            if handler is None:
                self._log.debug("No handler", slug)
                return

            async def send(instruction: IORender):
                if self._server_rpc is None:
                    raise Exception("server_rpc not initialized")

                await self._server_rpc.send(
                    "SEND_IO_CALL",
                    SendIOCallInputs(
                        transaction_id=inputs.transaction_id, io_call=instruction.json()
                    ),
                )

            client = IOClient(logger=self._logger, send=send)

            self._io_response_handlers[inputs.transaction_id] = client.on_response

            ctx = ActionContext(
                user=inputs.user,
                params=deserialize_dates(inputs.params),
                environment=inputs.environment,
            )

            async def call_handler():
                if self._server_rpc is None:
                    raise Exception("server_rpc not initialized")

                try:
                    result: ActionResult
                    try:
                        sig = signature(handler)
                        params = sig.parameters
                        if len(params) == 0:
                            resp = await handler()  # type: ignore
                        elif len(params) == 1:
                            resp = await handler(client.io)  # type: ignore
                        elif len(params) == 2:
                            resp = await handler(client.io, ctx)  # type: ignore
                        else:
                            raise Exception(
                                "handler accepts invalid number of arguments"
                            )

                        result = ActionResult(
                            status="SUCCESS",
                            data=serialize_dates(resp),
                        )
                    except IOError as ioerr:
                        raise ioerr
                    except Exception as err:
                        self._log.error("Error in action handler", err)
                        self._log.print_exception(err)
                        result = ActionResult(
                            status="FAILURE",
                            data={"message": str(err)},  # FIXME: Proper message?
                        )
                    await self._server_rpc.send(
                        "MARK_TRANSACTION_COMPLETE",
                        MarkTransactionCompleteInputs(
                            transaction_id=inputs.transaction_id,
                            result=result.json(),
                        ),
                    )
                except IOError as ioerr:
                    if ioerr.kind == "CANCELED":
                        self._log.prod("Transaction canceled for action", slug)
                    elif ioerr.kind == "TRANSACTION_CLOSED":
                        self._log.prod(
                            "Attempted to make IO call after transaction already closed in action",
                            slug,
                        )
                except Exception as err:
                    self._log.debug("Uncaught exception:", err)
                    self._log.print_exception(err)

            _ = asyncio.create_task(call_handler(), name="call_handler")

        async def io_response(inputs: IOResponseInputs):
            self._log.debug("Got IO response", inputs)
            io_resp = IOResponse.parse_raw(inputs.value)
            print(io_resp)
            try:
                reply_handler = self._io_response_handlers[io_resp.transaction_id]
                await reply_handler(io_resp)
            except KeyError:
                self._log.debug("Missing reply handler for", inputs.transaction_id)

        self._server_rpc = DuplexRPCClient(
            communicator=self._isocket,
            can_call=ws_server_schema,
            can_respond_to=host_schema,
            handlers={
                "START_TRANSACTION": start_transaction,
                "IO_RESPONSE": io_response,
            },
        )

    async def _initialize_host(self):
        if self._isocket is None:
            raise Exception("isocket not initialized")

        if self._server_rpc is None:
            raise Exception("server_rpc not initialized")

        slugs = list(self._actions.keys())

        logged_in: InitializeHostReturns | None = await self._server_rpc.send(
            "INITIALIZE_HOST",
            InitializeHostInputs(
                api_key=self._api_key,
                callable_action_names=slugs,
                sdk_name="interval-py",
                sdk_version="dev",
            ),
        )

        if logged_in is None:
            raise Exception("The provided API key is not valid")

        if len(logged_in.invalid_slugs) > 0:
            self._log.warn("[Interval]", "⚠ Invalid slugs detected:", end="\n\n")

            for slug in logged_in.invalid_slugs:
                self._log.warn(" -", slug)

            self._log.warn(
                "Action slugs must contain only letters, numbers, underscores, periods, and hyphens.",
                start="\n",
            )

            if len(logged_in.invalid_slugs) == len(slugs):
                raise Exception("No valid slugs provided")

        self._log.prod("Connected! Access your actions at: ", logged_in.dashboard_url)
        self._log.debug("Host ID:", self._isocket.id)
