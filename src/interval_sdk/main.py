import asyncio, importlib.metadata, time, datetime, signal
from contextvars import ContextVar
from dataclasses import dataclass
from inspect import iscoroutine, signature, isfunction
from typing import Any, Optional, Callable, cast, Union
from urllib.parse import urlparse, urlunparse
from uuid import uuid4, UUID

import aiohttp
import websockets, websockets.client, websockets.exceptions
from pydantic import parse_raw_as


from .io_schema import (
    ActionResult,
    ButtonItemModel,
    IOFunctionReturnModel,
    SerializableRecord,
)
from .classes.io import IO
from .classes.action import Action
from .classes.page import Page
from .classes.isocket import ISocket
from .classes.logger import Logger, LogLevel
from .classes.io_client import IOClient, IOError, IORender, IOResponse
from .classes.rpc import DuplexRPCClient
from .classes.layout import (
    BasicLayoutModel,
    Layout,
    PageError,
    PageLayoutKey,
)
from .classes.transaction_loading_state import TransactionLoadingState
from .internal_rpc_schema import (
    AccessControlDefinition,
    ActionContext,
    ActionDefinition,
    ActionEnvironment,
    ClosePageInputs,
    DeliveryInstruction,
    DeliveryInstructionModel,
    EnqueueActionInputs,
    EnqueueActionReturns,
    DequeueActionInputs,
    DequeueActionReturns,
    HostSchemaMethodName,
    LoadingState,
    NotifyInputs,
    NotifyReturns,
    OpenPageInputs,
    OpenPageReturns,
    OpenPageReturnsError,
    OpenPageReturnsSuccess,
    OrganizationDef,
    PageContext,
    PageDefinition,
    SendLoadingCallInputs,
    SendLogInputs,
    SendRedirectInputs,
    StartTransactionInputs,
    SendPageInputs,
    SendIOCallInputs,
    MarkTransactionCompleteInputs,
    IOResponseInputs,
    WSServerSchemaMethodName,
    ws_server_schema,
    host_schema,
    InitializeHostInputs,
    InitializeHostReturns,
)
from .util import (
    DeserializableRecord,
    ensure_serialized,
    isoformat_datetime,
    serialize_dates,
    deserialize_dates,
)
from .handlers import IntervalActionHandler, IntervalPageHandler, IOResponseHandler
from .types import IntervalError, NotInitializedError


@dataclass
class QueuedAction:
    id: str
    assignee: Optional[str]
    params: Optional[SerializableRecord]


# Intentionally different from the pypi package name,
# `-py` suffix is superfluous there but important to us.
SDK_NAME = "interval-py"
sdk_version = "???"

io_var: ContextVar[IO] = ContextVar("io_var")
action_ctx_var: ContextVar[ActionContext] = ContextVar("action_ctx_var")
page_ctx_var: ContextVar[PageContext] = ContextVar("page_ctx_var")
ctx_var: ContextVar[Union[ActionContext, PageContext]] = ContextVar("ctx_var")
interval_context_var: ContextVar[
    tuple[IO, Union[ActionContext, PageContext]]
] = ContextVar("interval_context_var")

try:
    sdk_version = importlib.metadata.version(__package__)
except:
    pass


class Interval:
    class Routes:
        _interval: "Interval"

        def __init__(self, interval: "Interval"):
            self._interval = interval

        def add(self, slug: str, action_or_page: Union[Action, Page]):
            if isinstance(action_or_page, Page):
                action_or_page._on_change = self._interval._handle_routes_change

            self._interval._routes[slug] = action_or_page
            self._interval._handle_routes_change()

        def remove(self, slug: str):
            try:
                action_or_page = self._interval._routes[slug]
                if isinstance(action_or_page, Page):
                    action_or_page._on_change = None

                del self._interval._routes[slug]
                self._interval._handle_routes_change()
            except KeyError:
                pass

        async def enqueue(
            self,
            slug: str,
            assignee_email: Optional[str] = None,
            params: Optional[SerializableRecord] = None,
        ) -> QueuedAction:
            try:
                params = cast(DeserializableRecord, serialize_dates(params))
                if params is not None:
                    try:
                        ensure_serialized(params)
                    except ValueError as e:
                        raise IntervalError(
                            "Invalid params, please pass an object of primitives."
                        ) from e

                try:
                    data = EnqueueActionInputs(
                        slug=slug,
                        assignee=assignee_email,
                        params=params,
                    ).json()
                except ValueError as e:
                    raise IntervalError("Invalid input.") from e

                async with aiohttp.ClientSession(
                    headers=self._interval._api_headers
                ) as session:
                    async with session.post(
                        self._interval._get_api_address("actions/enqueue"), data=data
                    ) as resp:
                        try:
                            text = await resp.text()
                            response = parse_raw_as(EnqueueActionReturns, text)
                        except Exception as e:
                            raise IntervalError("Received invalid API response.") from e

                if response.type == "error":
                    raise IntervalError(
                        f"There was a problem enqueueing the action: {response.message}."
                    )

                return QueuedAction(
                    id=response.id, assignee=assignee_email, params=params
                )
            except IntervalError as err:
                raise err
            except Exception as err:
                raise IntervalError(
                    "There was a problem enqueueing the action."
                ) from err

        async def dequeue(self, id: str) -> QueuedAction:
            try:
                try:
                    data = DequeueActionInputs(id=id).json()
                except ValueError as err:
                    raise IntervalError("Invalid input.") from err

                async with aiohttp.ClientSession(
                    headers=self._interval._api_headers
                ) as session:
                    async with session.post(
                        self._interval._get_api_address("actions/dequeue"), data=data
                    ) as resp:
                        try:
                            response = parse_raw_as(
                                DequeueActionReturns, await resp.text()
                            )
                        except Exception as err:
                            raise IntervalError(
                                "Received invalid API response."
                            ) from err

                if response.type == "error":
                    raise IntervalError(
                        f"There was a problem enqueueing the action: {response.message}."
                    )

                return QueuedAction(
                    id=response.id, assignee=response.assignee, params=response.params
                )
            except IntervalError as err:
                raise err
            except Exception as err:
                raise IntervalError(
                    "There was a problem dequeueing the action."
                ) from err

    _logger: Logger
    _endpoint: str = "wss://interval.com/websocket"
    _http_endpoint: str
    _api_key: str

    _retry_interval_seconds: float = 3
    _ping_timeout_seconds: float = 5
    _ping_interval_seconds: float = 30
    _close_unresponsive_connection_timeout_seconds: float = 180
    _reinitialize_batch_timeout_seconds: float = 0.2
    _num_isocket_producers: int

    _page_io_clients: dict[str, IOClient]
    _page_futures: dict[str, asyncio.Task]
    _io_response_handlers: dict[str, IOResponseHandler]
    _pending_io_calls: dict[str, str]
    _transaction_loading_states: dict[str, LoadingState]

    _isocket: Optional[ISocket] = None
    _server_rpc: Optional[
        DuplexRPCClient[WSServerSchemaMethodName, HostSchemaMethodName]
    ] = None
    _intentionally_closed = False
    _is_connected = False
    _is_initialized = False

    routes: Routes

    organization: Optional[OrganizationDef] = None
    environment: Optional[ActionEnvironment] = None

    _routes: dict[str, Union[Action, Page]]
    _action_definitions: list[ActionDefinition]
    _page_definitions: list[PageDefinition]
    _action_handlers: dict[str, IntervalActionHandler]
    _page_handlers: dict[str, IntervalPageHandler]

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: Optional[str] = None,
        log_level: LogLevel = "info",
        retry_interval: float = 3,
        ping_timeout: float = 5,
        ping_interval: float = 30,
        close_unresponsive_connection_timeout: float = 180,
        reinitialize_batch_timeout: float = 0.2,
        num_message_producers: int = 1,
    ):
        self._api_key = api_key
        if endpoint is not None:
            self._endpoint = endpoint

        url = urlparse(self._endpoint)
        self._http_endpoint = urlunparse(
            url._replace(scheme=url.scheme.replace("ws", "http"), path="/api")
        )

        self._retry_interval_seconds = retry_interval
        self._ping_timeout_seconds = ping_timeout
        self._ping_interval_seconds = ping_interval
        self._close_unresponsive_connection_timeout_seconds = (
            close_unresponsive_connection_timeout
        )
        self._reinitialize_batch_timeout_seconds = reinitialize_batch_timeout
        self._num_isocket_producers = num_message_producers

        self._page_io_clients = {}
        self._page_futures = {}
        self._io_response_handlers = {}
        self._pending_io_calls = {}
        self._transaction_loading_states = {}
        self._routes = {}
        self._action_definitions = []
        self._page_definitions = []
        self._action_handlers = {}
        self._page_handlers = {}
        self._logger = Logger(log_level=log_level, prefix=self.__class__.__name__)
        self.routes = Interval.Routes(self)

    def _get_api_address(self, path: str) -> str:
        if path.startswith("/"):
            path = path[1:]

        return f"{self._http_endpoint}/{path}"

    @property
    def _api_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

    def _walk_routes(self):
        page_definitions: list[PageDefinition] = []
        action_definitions: list[ActionDefinition] = []
        action_handlers: dict[str, IntervalActionHandler] = {}
        page_handlers: dict[str, IntervalPageHandler] = {}

        def walk_page(group_slug: str, page: Page):
            page_definitions.append(
                PageDefinition(
                    slug=group_slug,
                    name=page.name,
                    description=page.description,
                    has_handler=page.handler is not None,
                    unlisted=page.unlisted,
                    access=page.access,
                )
            )

            if page.handler is not None:
                page_handlers[group_slug] = page.handler

            for (slug, route) in page.routes.items():
                if isinstance(route, Page):
                    walk_page(f"{group_slug}/{slug}", route)
                else:
                    action_definitions.append(
                        ActionDefinition(
                            group_slug=group_slug,
                            slug=slug,
                            name=route.name,
                            description=route.description,
                            backgroundable=route.backgroundable,
                            unlisted=route.unlisted,
                            access=route.access,
                        )
                    )

                    action_handlers[f"{group_slug}/{slug}"] = route.handler

        for slug, route in self._routes.items():
            if isinstance(route, Page):
                walk_page(slug, route)
            else:
                action_definitions.append(
                    ActionDefinition(
                        slug=slug,
                        name=route.name,
                        description=route.description,
                        backgroundable=route.backgroundable,
                        unlisted=route.unlisted,
                        access=route.access,
                    )
                )

                action_handlers[slug] = route.handler

        self._page_definitions = page_definitions
        self._action_definitions = action_definitions
        self._action_handlers = action_handlers
        self._page_handlers = page_handlers

    def action(
        self,
        handler_or_slug: Optional[Union[IntervalActionHandler, str]] = None,
        *,
        slug: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        backgroundable: bool = False,
        unlisted: bool = False,
        access: Optional[AccessControlDefinition] = None,
    ) -> Callable[[IntervalActionHandler], IntervalActionHandler]:
        def action_adder(handler: IntervalActionHandler):
            self.routes.add(
                slug
                if slug is not None
                else handler_or_slug
                if (handler_or_slug is not None and isinstance(handler_or_slug, str))
                else handler.__name__,
                Action(
                    handler=handler,
                    name=name,
                    description=description,
                    backgroundable=backgroundable,
                    unlisted=unlisted,
                    access=access,
                ),
            )
            return handler

        if handler_or_slug is not None and isfunction(handler_or_slug):
            action_adder(handler_or_slug)

        return action_adder

    def page(
        self,
        name: str,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        unlisted: bool = False,
        access: Optional[AccessControlDefinition] = None,
    ) -> Callable[[IntervalPageHandler], IntervalPageHandler]:
        def page_adder(handler: IntervalPageHandler):
            self.routes.add(
                slug if slug is not None else handler.__name__,
                Page(
                    handler=handler,
                    name=name,
                    description=description,
                    unlisted=unlisted,
                    access=access,
                ),
            )
            return handler

        return page_adder

    # def route(self, slug: Optional[str] = None) -> Callable[[Union[Action, Page]], None]:
    #     def adder(action_or_page: Union[Action, Page]):
    #         inner_slug = slug if slug is not None else action_or_page.__name__
    #         self._add_route(inner_slug, action_or_page)
    #
    #     return adder

    @property
    def _log(self):
        return self._logger

    @property
    def is_connected(self):
        return self._is_connected

    async def _send(
        self,
        method_name: WSServerSchemaMethodName,
        inputs: dict[str, Any],
    ):
        if self._server_rpc is None:
            raise NotInitializedError("server_rpc not initialized")

        while True:
            if self._is_connected:
                try:
                    return await self._server_rpc.send(method_name, inputs)
                except Exception as err:
                    self._log.debug("RPC call timed out, retrying in 3s...", err)
            else:
                self._log.debug("Not connected, retrying again in 3s...")

            await asyncio.sleep(self._retry_interval_seconds)

    async def _send_log(self, transaction_id: str, index: int, *args):
        if len(args) == 0:
            return

        data = " ".join([str(arg) for arg in args])
        if len(data) > 10000:
            data = (
                data[:10000]
                + "..."
                + "\n^ Warning: 10k logline character limit reached.\nTo avoid this error, try separating your data into multiple ctx.log() calls."
            )

        try:
            return await self._send(
                "SEND_LOG",
                SendLogInputs(
                    transaction_id=transaction_id,
                    data=data,
                    index=index,
                    # expects time in milliseconds for JS Dates
                    timestamp=time.time_ns() // 1000000,
                ).dict(),
            )
        except Exception as err:
            self._logger.error("Failed sending log to Interval", err)

    async def _send_redirect(self, inputs: SendRedirectInputs):
        response = await self._send("SEND_REDIRECT", inputs.dict())
        if not response:
            raise IntervalError("Failed sending redirect")

    def listen(
        self, done_callback: Optional[Callable[[asyncio.Task[None]], None]] = None
    ):
        loop = asyncio.get_event_loop()
        task = loop.create_task(self.listen_async())
        if done_callback is not None:
            task.add_done_callback(done_callback)

        for sig in {signal.SIGINT, signal.SIGTERM}:
            loop.add_signal_handler(sig, loop.stop)
        loop.run_forever()

    async def listen_async(self):
        await self._create_socket_connection(uuid4())
        self._create_rpc_client()
        await self._initialize_host()

    async def close(self):
        self._intentionally_closed = True
        self._server_rpc = None
        if self._isocket is not None:
            await self._isocket.close()
            self._isocket = None

        self._is_connected = False

    async def notify(
        self,
        message: str,
        title: Optional[str] = None,
        delivery: Optional[list[DeliveryInstruction]] = None,
        transaction_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ):
        await self._notify(
            NotifyInputs(
                message=message,
                transaction_id=transaction_id,
                title=title,
                delivery_instructions=[
                    DeliveryInstructionModel.parse_obj(d) for d in delivery
                ]
                if delivery is not None
                else None,
                idempotency_key=idempotency_key,
                created_at=isoformat_datetime(datetime.datetime.now()),
            )
        )

    async def _notify(self, inputs: NotifyInputs):
        if inputs.transaction_id is None and (
            self.environment == "development"
            or (
                self.environment is None
                and (self._api_key is None or not self._api_key.startswith("live_"))
            )
        ):
            self._logger.warn(
                "Calls to notify() outside of a transaction currently have no effect when Interval is instantiated with a development API key. Please use a live key to send notifications."
            )

        async with aiohttp.ClientSession(headers=self._api_headers) as session:
            async with session.post(
                self._get_api_address("notify"),
                data=inputs.json(exclude_none=True),
            ) as resp:
                try:
                    text = await resp.text()
                    response = parse_raw_as(NotifyReturns, text)
                except Exception as e:
                    raise IntervalError("Received invalid API response.") from e

                if response.type == "error":
                    raise IntervalError(
                        f"There was a problem sending the notification: {response.message}"
                    )

    async def _resend_pending_io_calls(self, ids_to_resend: Optional[list[str]] = None):
        if not self._is_connected:
            return

        if ids_to_resend is None:
            to_resend: dict[str, str] = dict(self._pending_io_calls)
        else:
            to_resend: dict[str, str] = {}
            for id in ids_to_resend:
                try:
                    to_resend[id] = self._pending_io_calls[id]
                except KeyError:
                    pass

        while len(to_resend) > 0:
            items = list(to_resend.items())
            responses = await asyncio.gather(
                *(
                    self._send(
                        "SEND_IO_CALL",
                        SendIOCallInputs(
                            transaction_id=transaction_id,
                            io_call=io_call,
                        ).dict(),
                    )
                    for transaction_id, io_call in items
                ),
                return_exceptions=True,
            )
            for i, response in enumerate(responses):
                transaction_id = items[i][0]
                if isinstance(response, BaseException):
                    if isinstance(response, IOError):
                        self._logger.warn(
                            "Failed resending pending IO call:", response.kind
                        )
                        if response.kind in ("CANCELED", "TRANSACTION_CLOSED"):
                            self._logger.debug(
                                "Aborting resending pending IO call:", response
                            )
                            try:
                                del to_resend[transaction_id]
                            except KeyError:
                                pass
                            try:
                                del self._pending_io_calls[transaction_id]
                            except KeyError:
                                pass
                else:
                    del to_resend[transaction_id]
                    if not response:
                        # Unsuccessful, don't retry again
                        try:
                            del self._pending_io_calls[transaction_id]
                        except KeyError:
                            pass

            if len(to_resend) > 0:
                self._logger.debug(
                    f"Trying again in {self._retry_interval_seconds}s..."
                )
                await asyncio.sleep(self._retry_interval_seconds)

    async def _resend_transaction_loading_states(
        self, ids_to_resend: Optional[list[str]] = None
    ):
        if not self._is_connected:
            return

        if ids_to_resend is None:
            to_resend: dict[str, LoadingState] = dict(self._transaction_loading_states)
        else:
            to_resend: dict[str, LoadingState] = {}
            for id in ids_to_resend:
                try:
                    to_resend[id] = self._transaction_loading_states[id]
                except KeyError:
                    pass

        while len(to_resend) > 0:
            items = list(to_resend.items())
            responses = await asyncio.gather(
                (
                    self._send(
                        "SEND_LOADING_CALL",
                        SendLoadingCallInputs(
                            transaction_id=transaction_id,
                            **loading_state.dict(),
                        ).dict(),
                    )
                    for transaction_id, loading_state in items
                ),
                return_exceptions=True,
            )
            for i, response in enumerate(responses):
                transaction_id = items[i][0]
                if isinstance(response, BaseException):
                    if isinstance(response, IOError):
                        self._logger.warn(
                            "Failed resending loading call:", response.kind
                        )
                        if (
                            response.kind == "CANCELED"
                            or response.kind == "TRANSACTION_CLOSED"
                        ):
                            self._logger.debug(
                                "Aborting resending loading call:", response
                            )
                            try:
                                del to_resend[transaction_id]
                            except KeyError:
                                pass
                            try:
                                del self._transaction_loading_states[transaction_id]
                            except KeyError:
                                pass
                else:
                    try:
                        del to_resend[transaction_id]
                    except KeyError:
                        pass
                    if not response:
                        # Unsuccessful, don't retry again
                        try:
                            del self._transaction_loading_states[transaction_id]
                        except KeyError:
                            pass

            if len(to_resend) > 0:
                self._logger.debug(
                    f"Trying again in {self._retry_interval_seconds}s..."
                )
                await asyncio.sleep(self._retry_interval_seconds)

    async def _create_socket_connection(self, instance_id: UUID):
        async def on_close(code: int, reason: str):
            if self._intentionally_closed:
                self._intentionally_closed = False
                return

            if not self._is_connected:
                return

            self._log.prod(
                f"Lost connection to Interval (code {code}). Reason: {reason}"
            )
            self._log.prod("Reconnecting...")
            self._is_connected = False

            while not self._is_connected:
                try:
                    await self._create_socket_connection(instance_id=instance_id)
                    self._log.prod("Reconnection successful")
                    self._is_connected = True
                    await asyncio.gather(
                        self._resend_pending_io_calls(),
                        self._resend_transaction_loading_states(),
                    )
                except Exception as err:
                    self._log.prod("Unable to reconnect. Retrying in 3s...")
                    self._log.debug(err)
                    await asyncio.sleep(3)

        ws = await websockets.client.connect(
            self._endpoint,
            extra_headers={
                "x-api-key": self._api_key,
                "x-instance-id": str(instance_id),
            },
            open_timeout=10,
            ping_interval=self._ping_interval_seconds,
            ping_timeout=self._ping_timeout_seconds,
        )

        self._isocket = ISocket(
            id=instance_id,
            ws=ws,
            on_close=on_close,
            log_level=self._logger.log_level,
            num_producers=self._num_isocket_producers,
        )

        await self._isocket.connect()
        self._is_connected = True

        if self._server_rpc is None:
            return

        self._server_rpc.set_communicator(self._isocket)
        await self._initialize_host()

    def _create_rpc_client(self):
        loop = asyncio.get_running_loop()

        if self._isocket is None:
            raise NotInitializedError("ISocket not initialized")

        async def start_transaction(inputs: StartTransactionInputs) -> None:
            if self.organization is None:
                self._logger.error("No organization defined")
                return

            if inputs.transaction_id in self._io_response_handlers:
                self._logger.debug("Transaction already started, not starting again")

            slug = inputs.action.slug
            handler = self._action_handlers.get(slug, None)

            if handler is None:
                self._log.debug("No handler", slug)
                return

            async def send(instruction: IORender):
                io_call = instruction.json(exclude_unset=True)
                self._pending_io_calls[inputs.transaction_id] = io_call
                await self._send(
                    "SEND_IO_CALL",
                    SendIOCallInputs(
                        transaction_id=inputs.transaction_id,
                        io_call=io_call,
                    ).dict(),
                )

            async def send_loading_state(loading_state: LoadingState):
                self._transaction_loading_states[inputs.transaction_id] = loading_state
                await self._send(
                    "SEND_LOADING_CALL",
                    SendLoadingCallInputs(
                        transaction_id=inputs.transaction_id,
                        **loading_state.dict(),
                    ).dict(),
                )

            client = IOClient(logger=self._logger, send=send)

            self._io_response_handlers[inputs.transaction_id] = client.on_response

            action_ctx = ActionContext(
                transaction_id=inputs.transaction_id,
                logger=self._logger,
                user=inputs.user,
                params=deserialize_dates(inputs.params),
                environment=inputs.environment,
                organization=self.organization,
                action=inputs.action,
                send_log=self._send_log,
                send_redirect=self._send_redirect,
                notify=self._notify,
                loading=TransactionLoadingState(
                    logger=self._logger,
                    sender=send_loading_state,
                ),
            )

            async def handle_action():
                try:
                    result: ActionResult
                    io_token = io_var.set(client.io)
                    action_ctx_token = action_ctx_var.set(action_ctx)
                    ctx_token = ctx_var.set(action_ctx)
                    interval_context_token = interval_context_var.set(
                        (client.io, action_ctx)
                    )

                    try:
                        sig = signature(handler)
                        params = sig.parameters
                        if len(params) == 0:
                            resp = await handler()  # type: ignore
                        elif len(params) == 1:
                            resp = await handler(client.io)  # type: ignore
                        elif len(params) == 2:
                            resp = await handler(client.io, action_ctx)  # type: ignore
                        else:
                            raise IntervalError(
                                "handler accepts invalid number of arguments"
                            )

                        if resp is not None and not isinstance(
                            resp,
                            (
                                bool,
                                int,
                                float,
                                datetime.date,
                                datetime.time,
                                datetime.datetime,
                                str,
                            ),
                        ):
                            resp = dict(resp.items())

                        result = ActionResult(
                            status="SUCCESS",
                            data=IOFunctionReturnModel.parse_obj(serialize_dates(resp)),
                        )
                    except IOError as ioerr:
                        raise ioerr
                    except Exception as err:
                        self._log.error("Error in action handler", err)
                        self._log.print_exception(err)
                        result = ActionResult(
                            status="FAILURE",
                            data=IOFunctionReturnModel.parse_obj(
                                {
                                    "error": err.__class__.__name__,
                                    "message": str(err),
                                }
                            ),
                        )
                    finally:
                        io_var.reset(io_token)
                        action_ctx_var.reset(action_ctx_token)
                        ctx_var.reset(ctx_token)
                        interval_context_var.reset(interval_context_token)
                    await self._send(
                        "MARK_TRANSACTION_COMPLETE",
                        MarkTransactionCompleteInputs(
                            transaction_id=inputs.transaction_id,
                            result=result.json(),
                        ).dict(),
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
                finally:
                    try:
                        del self._pending_io_calls[inputs.transaction_id]
                    except KeyError:
                        pass
                    try:
                        del self._io_response_handlers[inputs.transaction_id]
                    except KeyError:
                        pass

            task = loop.create_task(handle_action(), name="handle_action")
            # this should never be hit, exceptions handled in function
            task.add_done_callback(self._logger.handle_task_exceptions)

        async def io_response(inputs: IOResponseInputs) -> None:
            self._log.debug("Got IO response", inputs)
            io_resp = IOResponse.parse_raw(inputs.value)
            try:
                reply_handler = self._io_response_handlers[io_resp.transaction_id]
                await reply_handler(io_resp)
            except KeyError:
                self._log.debug("Missing reply handler for", inputs.transaction_id)

        async def open_page(inputs: OpenPageInputs) -> OpenPageReturns:
            self._logger.debug("OPEN_PAGE", inputs)

            if self.organization is None:
                self._logger.error("No organization defined")
                return OpenPageReturnsError(
                    message="No organization defined.",
                )

            try:
                page_handler = self._page_handlers[inputs.page.slug]
            except KeyError:
                self._logger.error("No page handler found for slug", inputs.page.slug)
                return OpenPageReturnsError(message="No page handler found.")

            # TODO superjson paramsMeta
            page_ctx = PageContext(
                user=inputs.user,
                params=deserialize_dates(inputs.params),
                environment=inputs.environment,
                organization=self.organization,
                page=inputs.page,
            )

            page: Optional[Layout] = None
            menu_items: Optional[list[ButtonItemModel]] = None
            render_instruction: Optional[IORender] = None
            errors: list[PageError] = []

            MAX_PAGE_RETRIES = 5

            send_page_task: Optional[asyncio.Task] = None

            def on_page_sent(task: asyncio.Task):
                nonlocal send_page_task
                try:
                    task.result()
                    send_page_task = None
                except BaseException as e:
                    self._logger.error(e)

            async def send_page():
                if page is not None:
                    page_layout = BasicLayoutModel(
                        kind="BASIC",
                        errors=errors,
                    )

                    if page.title is not None:
                        page_layout.title = (
                            page.title if isinstance(page.title, str) else None
                        )

                    if page.description is not None:
                        page_layout.description = (
                            page.description
                            if isinstance(page.description, str)
                            else None
                        )

                    if render_instruction is not None:
                        page_layout.children = render_instruction

                    if menu_items is not None:
                        page_layout.menu_items = menu_items

                    for _ in range(MAX_PAGE_RETRIES):
                        try:
                            await self._send(
                                "SEND_PAGE",
                                SendPageInputs(
                                    page_key=inputs.page_key,
                                    page=page_layout.json(exclude_unset=True),
                                ).dict(),
                            )
                            return
                        except Exception as err:
                            self._logger.debug("Failed sending page", err)
                            self._logger.debug(
                                "Retrying in", self._retry_interval_seconds, "seconds"
                            )
                            await asyncio.sleep(self._retry_interval_seconds)
                    raise IntervalError(
                        "Unsuccessful sending page, max retries exceeded."
                    )

            async def handle_send(instruction: IORender):
                nonlocal render_instruction
                render_instruction = instruction
                if send_page_task is None:
                    await send_page()

            client = IOClient(logger=self._logger, send=handle_send)

            self._page_io_clients[inputs.page_key] = client
            self._io_response_handlers[inputs.page_key] = client.on_response

            def page_error(
                error: BaseException, layout_key: PageLayoutKey
            ) -> PageError:
                return PageError(
                    layout_key=layout_key,
                    error=error.__class__.__name__,
                    message=str(error),
                )

            async def handle_page():
                nonlocal page, menu_items, send_page_task
                io_token = io_var.set(client.io)
                page_ctx_token = page_ctx_var.set(page_ctx)
                ctx_token = ctx_var.set(page_ctx)
                interval_context_token = interval_context_var.set((client.io, page_ctx))
                try:
                    sig = signature(page_handler)
                    params = sig.parameters
                    if len(params) == 0:
                        resp = await page_handler()  # type: ignore
                    elif len(params) == 1:
                        resp = await page_handler(client.io.display)  # type: ignore
                    elif len(params) == 2:
                        resp = await page_handler(client.io.display, page_ctx)  # type: ignore
                    else:
                        raise IntervalError(
                            "handler accepts invalid number of arguments"
                        )

                    page = resp

                    if page.title is not None:
                        if isfunction(page.title):
                            try:
                                page.title = page.title()
                            except Exception as err:
                                self._logger.error(err)
                                errors.append(page_error(err, "title"))

                        if iscoroutine(page.title):
                            title_task = loop.create_task(page.title)

                            def handle_title(task: asyncio.Task[str]):
                                nonlocal send_page_task
                                try:
                                    del self._page_futures[task.get_name()]
                                except:
                                    pass

                                if page is None:
                                    return

                                try:
                                    page.title = task.result()
                                except Exception as err:
                                    errors.append(page_error(err, "description"))

                                if send_page_task is None:
                                    send_page_task = loop.create_task(send_page())
                                    send_page_task.add_done_callback(on_page_sent)

                            title_task.add_done_callback(handle_title)
                            self._page_futures[title_task.get_name()] = title_task

                    if page.description is not None:
                        if isfunction(page.description):
                            try:
                                page.description = page.description()
                            except Exception as err:
                                self._logger.error(err)
                                errors.append(page_error(err, "description"))

                        if iscoroutine(page.description):
                            desc_task = loop.create_task(page.description)

                            def handle_desc(task: asyncio.Task[str]):
                                nonlocal send_page_task
                                try:
                                    del self._page_futures[task.get_name()]
                                except:
                                    pass

                                if page is None:
                                    return

                                try:
                                    page.description = task.result()
                                except Exception as err:
                                    errors.append(page_error(err, "description"))
                                if send_page_task is None:
                                    send_page_task = loop.create_task(send_page())
                                    send_page_task.add_done_callback(on_page_sent)

                            desc_task.add_done_callback(handle_desc)
                            self._page_futures[desc_task.get_name()] = desc_task

                    if page.menu_items:
                        menu_items = [
                            ButtonItemModel.parse_obj(item) for item in page.menu_items
                        ]

                    if page.children is not None:
                        render_task = loop.create_task(
                            client.render_components(
                                [p._component for p in page.children]
                            )
                        )

                        def handle_children(task: asyncio.Task):
                            nonlocal send_page_task
                            try:
                                del self._page_futures[task.get_name()]
                            except:
                                pass

                            try:
                                task.result()
                                self._logger.debug(
                                    "Initial children render complete for page_key",
                                    inputs.page_key,
                                )
                            except IOError as err:
                                self._logger.error(err)
                                if err.__cause__ is not None:
                                    errors.append(
                                        page_error(err.__cause__, layout_key="children")
                                    )
                                else:
                                    errors.append(page_error(err, "children"))

                                if send_page_task is None:
                                    send_page_task = loop.create_task(send_page())
                                    send_page_task.add_done_callback(on_page_sent)
                            except Exception as err:
                                self._logger.error(err)
                                errors.append(page_error(err, layout_key="children"))
                                if send_page_task is None:
                                    send_page_task = loop.create_task(send_page())
                                    send_page_task.add_done_callback(on_page_sent)

                        render_task.add_done_callback(handle_children)
                        self._page_futures[render_task.get_name()] = render_task
                except Exception as err:
                    self._logger.error("Error in page:", err)
                    page_layout = BasicLayoutModel(kind="BASIC", errors=errors)

                    await self._send(
                        "SEND_PAGE",
                        SendPageInputs(
                            page_key=inputs.page_key,
                            page=page_layout.json(),
                        ).dict(),
                    )
                finally:
                    io_var.reset(io_token)
                    ctx_var.reset(ctx_token)
                    page_ctx_var.reset(page_ctx_token)
                    interval_context_var.reset(interval_context_token)

            def handle_page_error(task: asyncio.Task):
                try:
                    task.result()
                except asyncio.CancelledError:
                    pass
                except BaseException as err:
                    errors.append(page_error(err, layout_key="children"))

            task = loop.create_task(handle_page(), name="handle_page")
            task.add_done_callback(handle_page_error)
            self._page_futures[inputs.page_key] = task

            return OpenPageReturnsSuccess(page_key=inputs.page_key)

        async def close_page(inputs: ClosePageInputs) -> None:
            self._logger.debug("CLOSE_PAGE", inputs)
            try:
                del self._page_io_clients[inputs.page_key]
            except KeyError:
                pass

            try:
                fut = self._page_futures[inputs.page_key]
                fut.cancel()
                del self._page_futures[inputs.page_key]
            except KeyError:
                pass

            try:
                del self._io_response_handlers[inputs.page_key]
            except KeyError:
                pass

        self._server_rpc = DuplexRPCClient(
            communicator=self._isocket,
            can_call=ws_server_schema,
            can_respond_to=host_schema,
            handlers={
                "START_TRANSACTION": start_transaction,
                "IO_RESPONSE": io_response,
                "OPEN_PAGE": open_page,
                "CLOSE_PAGE": close_page,
            },
            log_level=self._logger.log_level,
        )

    async def _initialize_host(self):
        if self._isocket is None:
            raise NotInitializedError("isocket not initialized")

        is_initial_initialization = not self._is_initialized
        self._is_initialized = True

        self._walk_routes()

        try:
            response: Optional[InitializeHostReturns] = await self._send(
                "INITIALIZE_HOST",
                InitializeHostInputs(
                    actions=self._action_definitions,
                    groups=self._page_definitions,
                    sdk_name=SDK_NAME,
                    sdk_version=sdk_version,
                ).dict(exclude_none=True),
            )
        except Exception as err:
            self._log.debug(err)
            self._log.print_exception(err)
            raise err

        if response is None:
            raise IntervalError("Unknown error")

        if response.sdk_alert:
            self._logger.handle_sdk_alert(response.sdk_alert)

        if response.type == "error":
            raise IntervalError(response.message)

        if len(response.invalid_slugs) > 0:
            self._logger.warn("[Interval]", "⚠ Invalid slugs detected:", end="\n\n")

            for slug in response.invalid_slugs:
                self._log.warn(" -", slug)

            self._logger.warn(
                "Action slugs must contain only letters, numbers, underscores, periods, and hyphens.",
                start="\n",
            )

        for warning in response.warnings:
            self._logger.warn(warning)

        if is_initial_initialization:
            self._log.prod(
                "Connected! Access your actions at: ", response.dashboard_url
            )

            if self._isocket is not None:
                self._log.debug("Host ID:", self._isocket.id)

        self.organization = response.organization

        return response

    _reinitialize_task: Optional[asyncio.Task] = None

    async def _reinitialize_routes(self):
        await asyncio.sleep(self._reinitialize_batch_timeout_seconds)
        await self._initialize_host()

    def _handle_routes_change(self):
        if not self._is_initialized or self._reinitialize_task is not None:
            return

        def on_complete(task: asyncio.Task):
            try:
                task.result()
                self._reinitialize_task = None
            except BaseException as e:
                self._logger.error("Failed reinitializing routes:", e)

        loop = asyncio.get_running_loop()

        self._reinitialize_task = loop.create_task(self._reinitialize_routes())
        self._reinitialize_task.add_done_callback(on_complete)
