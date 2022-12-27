import asyncio, importlib.metadata
from dataclasses import dataclass
from inspect import signature
from typing import Any, Optional, Callable, cast
from urllib.parse import urlparse, urlunparse
from uuid import uuid4, UUID

import aiohttp
import websockets, websockets.client, websockets.exceptions
from pydantic import parse_raw_as

from .io_schema import (
    ActionResult,
    IOFunctionReturnModel,
    SerializableRecord,
)
from .classes.action import Action
from .classes.page import Page
from .classes.isocket import ISocket
from .classes.logger import Logger, LogLevel
from .classes.io_client import IOClient, IOError, IORender, IOResponse
from .classes.rpc import DuplexRPCClient
from .internal_rpc_schema import (
    ActionContext,
    ActionDefinition,
    ActionEnvironment,
    EnqueueActionInputs,
    EnqueueActionReturns,
    DequeueActionInputs,
    DequeueActionReturns,
    HostSchemaMethodName,
    OrganizationDef,
    PageDefinition,
    StartTransactionInputs,
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
    serialize_dates,
    deserialize_dates,
)
from .handlers import IntervalActionHandler, IntervalPageHandler, IOResponseHandler
from .types import BaseModel


@dataclass
class QueuedAction:
    id: str
    assignee: str | None
    params: SerializableRecord | None


class NotInitializedError(Exception):
    pass


class IntervalError(Exception):
    pass


# Intentionally different from the pypi package name,
# `-py` suffix is superfluous there but important to us.
SDK_NAME = "interval-py"
sdk_version = "???"

try:
    sdk_version = importlib.metadata.version(__package__)
except:
    pass


class Interval:
    class Actions:
        _api_key: str
        _endpoint: str

        def __init__(self, api_key: str, endpoint: str):
            self._api_key = api_key
            url = urlparse(endpoint)
            self._endpoint = urlunparse(
                url._replace(
                    scheme=url.scheme.replace("ws", "http"), path="/api/actions"
                )
            )

        def _get_address(self, path: str) -> str:
            if path.startswith("/"):
                path = path[1:]

            return f"{self._endpoint}/{path}"

        @property
        def _headers(self) -> dict:
            return {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            }

        async def enqueue(
            self,
            slug: str,
            assignee_email: str | None = None,
            params: SerializableRecord | None = None,
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

                async with aiohttp.ClientSession(headers=self._headers) as session:
                    async with session.post(
                        self._get_address("enqueue"), data=data
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

                async with aiohttp.ClientSession(headers=self._headers) as session:
                    async with session.post(
                        self._get_address("dequeue"), data=data
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
    _api_key: str

    _io_response_handlers: dict[str, IOResponseHandler] = {}
    _isocket: ISocket | None = None
    _server_rpc: DuplexRPCClient[
        WSServerSchemaMethodName, HostSchemaMethodName
    ] | None = None
    _is_connected = False
    _is_initialized = False

    actions: Actions

    organization: OrganizationDef | None = None
    environment: ActionEnvironment | None = None

    _routes: dict[str, Action | Page] = {}
    _action_definitions: list[ActionDefinition] = []
    _page_definitions: list[PageDefinition] = []
    _action_handlers: dict[str, IntervalActionHandler]
    _page_handlers: dict[str, IntervalPageHandler]

    def __init__(
        self,
        api_key: str,
        endpoint: Optional[str] = None,
        log_level: LogLevel = "info",
    ):
        self._api_key = api_key
        if endpoint is not None:
            self._endpoint = endpoint

        self._action_handlers = {}
        self._logger = Logger(log_level)
        self.actions = Interval.Actions(self._api_key, self._endpoint)

    def walk_routes(self):
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

    def action(self, action_handler: IntervalActionHandler) -> None:
        return self._add_route(action_handler.__name__, Action(handler=action_handler))

    def action_with_slug(self, slug: str) -> Callable[[IntervalActionHandler], None]:
        def action_adder(action_handler: IntervalActionHandler):
            self._add_route(slug, Action(handler=action_handler))

        return action_adder

    # TODO: Try inferring this slug
    def route(self, slug: str) -> Callable[[Action | Page], None]:
        def adder(action_or_page: Action | Page):
            self._add_route(slug, action_or_page)

        return adder

    def _add_route(self, slug: str, action_or_page: Action | Page) -> None:
        self._routes[slug] = action_or_page

    @property
    def _log(self):
        return self._logger

    @property
    def is_connected(self):
        return self._is_connected

    async def _send(
        self, method_name: WSServerSchemaMethodName, inputs: dict[str, Any]
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

            await asyncio.sleep(3)

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

            if self._isocket is not None:
                # Must be sure to close the previous connection or its
                # producer/consumer loops will continue forever.
                await self._isocket.close()

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
            raise NotInitializedError("ISocket not initialized")

        async def start_transaction(inputs: StartTransactionInputs):
            if self.organization is None:
                self._logger.error("No organization defined")
                return

            slug = inputs.action.slug
            handler = self._action_handlers.get(slug, None)

            if handler is None:
                self._log.debug("No handler", slug)
                return

            async def send(instruction: IORender):
                await self._send(
                    "SEND_IO_CALL",
                    SendIOCallInputs(
                        transaction_id=inputs.transaction_id,
                        io_call=instruction.json(exclude_unset=True),
                    ).dict(),
                )

            client = IOClient(logger=self._logger, send=send)

            self._io_response_handlers[inputs.transaction_id] = client.on_response

            ctx = ActionContext(
                user=inputs.user,
                params=deserialize_dates(inputs.params),
                environment=inputs.environment,
                organization=self.organization,
                action=inputs.action,
            )

            async def call_handler():
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
                                # FIXME: Proper message?
                                {"message": str(err)}
                            ),
                        )
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

            _ = asyncio.create_task(call_handler(), name="call_handler")

        async def io_response(inputs: IOResponseInputs):
            self._log.debug("Got IO response", inputs)
            io_resp = IOResponse.parse_raw(inputs.value)
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
            raise NotInitializedError("isocket not initialized")

        is_initial_initialization = not self._is_initialized
        self._is_initialized = True

        self.walk_routes()

        try:
            response: InitializeHostReturns | None = await self._send(
                "INITIALIZE_HOST",
                InitializeHostInputs(
                    api_key=self._api_key,
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
