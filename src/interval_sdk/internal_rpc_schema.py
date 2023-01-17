from dataclasses import dataclass as base_dataclass
from datetime import datetime
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    Type,
    Literal,
    TypeVar,
    Union,
)
from typing_extensions import Annotated, NotRequired, TypeAlias, TypedDict, Awaitable

from pydantic import Field
from pydantic.dataclasses import dataclass

from .classes.logger import Logger, SdkAlert
from .classes.transaction_loading_state import LoadingState, TransactionLoadingState

from .util import SerializableRecord, isoformat_datetime, json_dumps_strip_none
from .types import BaseModel, GenericModel


ActionEnvironment: TypeAlias = Literal["live", "development"]


@base_dataclass
class RPCMethod:
    inputs: Type
    returns: Type


MethodDef: TypeAlias = dict[str, RPCMethod]


class ConnectToTransactionAsClientInputs(BaseModel):
    transaction_id: str
    instance_id: str


class RespondToIoCallInputs(BaseModel):
    transaction_id: str
    io_response: str


class SendIOCallInputs(BaseModel):
    transaction_id: str
    io_call: str


class SendPageInputs(BaseModel):
    page_key: str
    # stringified page
    page: str


class LeavePageInputs(BaseModel):
    page_key: str


class SendLoadingCallInputs(LoadingState):
    transaction_id: str
    label: Optional[str] = None


class SendLogInputs(BaseModel):
    transaction_id: str
    data: str
    index: Optional[int] = None
    timestamp: Optional[int] = None


class DeliveryInstruction(TypedDict):
    to: str
    method: NotRequired[Literal["EMAIL", "SLACK"]]


class DeliveryInstructionModel(BaseModel):
    to: str
    method: Optional[Literal["EMAIL", "SLACK"]] = None

    class Config:
        json_dumps = json_dumps_strip_none


class NotifyInputs(BaseModel):
    message: str
    transaction_id: Optional[str] = None
    title: Optional[str] = None
    idempotency_key: Optional[str] = None
    delivery_instructions: Optional[list[DeliveryInstructionModel]] = None
    created_at: str


class NotifyReturnsSuccess(BaseModel):
    type: Literal["success"] = "success"


class NotifyReturnsError(BaseModel):
    type: Literal["error"] = "error"
    message: str


NotifyReturns = Annotated[
    Union[NotifyReturnsSuccess, NotifyReturnsError], Field(discriminator="type")
]


class SendRedirectInputs(BaseModel):
    transaction_id: str
    url: Optional[str] = None
    route: Optional[str] = None
    params: Optional[SerializableRecord] = None


class MarkTransactionCompleteInputs(BaseModel):
    transaction_id: str
    result: Optional[str]


class AccessControlObjectDefinition(TypedDict):
    teams: list[str]


AccessControlDefinition: TypeAlias = Union[
    Literal["entire-organization"], AccessControlObjectDefinition
]


class ActionDefinition(BaseModel):
    group_slug: Optional[str] = None
    slug: str
    name: Optional[str] = None
    description: Optional[str] = None
    backgroundable: bool = False
    unlisted: bool = False
    access: Optional[AccessControlDefinition] = None


class PageDefinition(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    has_handler: bool = False
    unlisted: bool = False
    access: Optional[AccessControlDefinition] = None


class InitializeHostInputs(BaseModel):
    sdk_name: str
    sdk_version: str
    actions: list[ActionDefinition]
    groups: list[PageDefinition]


@dataclass
class OrganizationDef:
    name: str
    slug: str


class InitializeHostReturnsSuccess(BaseModel):
    type: Literal["success"] = "success"
    environment: ActionEnvironment
    invalid_slugs: list[str]
    organization: OrganizationDef
    dashboard_url: str
    sdk_alert: Optional[SdkAlert] = None
    warnings: list[str]


class InitializeHostReturnsError(BaseModel):
    type: Literal["error"] = "error"
    message: str
    sdk_alert: Optional[SdkAlert] = None


InitializeHostReturns = Annotated[
    Union[InitializeHostReturnsSuccess, InitializeHostReturnsError],
    Field(discriminator="type"),
]


class EnqueueActionInputs(BaseModel):
    slug: str
    assignee: Optional[str]
    params: Optional[SerializableRecord]


class EnqueueActionReturnsSuccess(BaseModel):
    type: Literal["success"] = "success"
    id: str


class EnqueueActionReturnsError(BaseModel):
    type: Literal["error"] = "error"
    message: str


EnqueueActionReturns = Annotated[
    Union[EnqueueActionReturnsSuccess, EnqueueActionReturnsError],
    Field(discriminator="type"),
]


class DequeueActionInputs(BaseModel):
    id: str


class DequeueActionReturnsSuccess(BaseModel):
    type: Literal["success"] = "success"
    id: str
    assignee: Optional[str]
    params: Optional[SerializableRecord]


class DequeueActionReturnsError(BaseModel):
    type: Literal["error"] = "error"
    message: str


DequeueActionReturns = Annotated[
    Union[DequeueActionReturnsSuccess, DequeueActionReturnsError],
    Field(discriminator="type"),
]

WSServerSchemaMethodName = Literal[
    "CONNECT_TO_TRANSACTION_AS_CLIENT",
    "RESPOND_TO_IO_CALL",
    "SEND_IO_CALL",
    "SEND_LOADING_CALL",
    "SEND_LOG",
    "NOTIFY",
    "SEND_REDIRECT",
    "SEND_PAGE",
    "LEAVE_PAGE",
    "MARK_TRANSACTION_COMPLETE",
    "INITIALIZE_HOST",
    "ENQUEUE_ACTION",
    "DEQUEUE_ACTION",
]

WSServerSchema = dict[WSServerSchemaMethodName, RPCMethod]

ws_server_schema: WSServerSchema = {
    "CONNECT_TO_TRANSACTION_AS_CLIENT": RPCMethod(
        inputs=ConnectToTransactionAsClientInputs,
        returns=bool,
    ),
    "RESPOND_TO_IO_CALL": RPCMethod(
        inputs=RespondToIoCallInputs,
        returns=bool,
    ),
    "SEND_IO_CALL": RPCMethod(
        inputs=SendIOCallInputs,
        returns=bool,
    ),
    "SEND_PAGE": RPCMethod(
        inputs=SendPageInputs,
        returns=bool,
    ),
    "LEAVE_PAGE": RPCMethod(
        inputs=LeavePageInputs,
        returns=bool,
    ),
    "SEND_LOADING_CALL": RPCMethod(
        inputs=SendLoadingCallInputs,
        returns=bool,
    ),
    "SEND_LOG": RPCMethod(
        inputs=SendLogInputs,
        returns=bool,
    ),
    "NOTIFY": RPCMethod(
        inputs=NotifyInputs,
        returns=bool,
    ),
    "SEND_REDIRECT": RPCMethod(
        inputs=SendRedirectInputs,
        returns=bool,
    ),
    "MARK_TRANSACTION_COMPLETE": RPCMethod(
        inputs=MarkTransactionCompleteInputs,
        returns=bool,
    ),
    "INITIALIZE_HOST": RPCMethod(
        inputs=InitializeHostInputs,
        returns=InitializeHostReturns,
    ),
    "ENQUEUE_ACTION": RPCMethod(
        inputs=EnqueueActionInputs,
        returns=EnqueueActionReturns,
    ),
    "DEQUEUE_ACTION": RPCMethod(
        inputs=DequeueActionInputs,
        returns=DequeueActionReturns,
    ),
}


class RenderInputs(BaseModel):
    toRender: str


ClientSchemaMethodName = Literal[
    "CLIENT_USURPED",
    "TRANSACTION_COMPLETED",
    "HOST_CLOSED_UNEXPECTEDLY",
    "HOST_RECONNECTED",
    "RENDER",
]

ClientSchema = dict[ClientSchemaMethodName, RPCMethod]

client_schema: ClientSchema = {
    "CLIENT_USURPED": RPCMethod(
        inputs=None,
        returns=None,
    ),
    "TRANSACTION_COMPLETED": RPCMethod(
        inputs=None,
        returns=None,
    ),
    "HOST_CLOSED_UNEXPECTEDLY": RPCMethod(
        inputs=None,
        returns=None,
    ),
    "HOST_RECONNECTED": RPCMethod(
        inputs=None,
        returns=None,
    ),
    "RENDER": RPCMethod(
        inputs=RenderInputs,
        returns=None,
    ),
}


class IOResponseInputs(BaseModel):
    value: str
    transaction_id: str


@dataclass
class ContextUser:
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@dataclass
class ActionInfo:
    slug: str
    url: str


class ActionContext:
    environment: ActionEnvironment
    user: ContextUser
    params: SerializableRecord
    organization: OrganizationDef
    action: ActionInfo
    loading: TransactionLoadingState

    _transaction_id: str
    _logger: Logger
    _send_redirect: Callable[[SendRedirectInputs], Awaitable[None]]
    _send_log: Callable[..., Awaitable[None]]
    _notify: Callable[[NotifyInputs], Awaitable[None]]
    _log_index = 0

    def __init__(
        self,
        transaction_id: str,
        logger: Logger,
        environment: ActionEnvironment,
        user: ContextUser,
        params: SerializableRecord,
        organization: OrganizationDef,
        action: ActionInfo,
        loading: TransactionLoadingState,
        send_log: Callable[..., Awaitable[None]],
        send_redirect: Callable[[SendRedirectInputs], Awaitable[None]],
        notify: Callable[[NotifyInputs], Awaitable[None]],
    ):
        self._transaction_id = transaction_id
        self._logger = logger
        self._send_log = send_log
        self._send_redirect = send_redirect
        self._notify = notify

        self.environment = environment
        self.user = user
        self.params = params
        self.organization = organization
        self.action = action
        self.loading = loading

    async def log(self, *args):
        self._log_index += 1
        await self._send_log(
            self._transaction_id,
            self._log_index,
            *args,
        )

    async def notify(
        self,
        message: str,
        title: Optional[str] = None,
        delivery: Optional[list[DeliveryInstruction]] = None,
        idempotency_key: Optional[str] = None,
    ):
        return await self._notify(
            NotifyInputs(
                message=message,
                title=title,
                delivery_instructions=[
                    DeliveryInstructionModel.parse_obj(d) for d in delivery
                ]
                if delivery is not None
                else None,
                transaction_id=self._transaction_id,
                idempotency_key=idempotency_key,
                created_at=isoformat_datetime(datetime.now()),
            )
        )

    async def redirect(
        self,
        url: Optional[str] = None,
        route: Optional[str] = None,
        params: Optional[SerializableRecord] = None,
    ):
        if (url is None and route is None) or (url is not None and route is not None):
            self._logger.error("Must specify exactly one of either `url` or `route`.")

        inputs = SendRedirectInputs(
            transaction_id=self._transaction_id,
        )

        if url is not None:
            inputs.url = url
        if route is not None:
            inputs.route = route
            if params is not None:
                inputs.params = params

        await self._send_redirect(inputs)


@dataclass
class PageInfo:
    slug: str


@dataclass
class PageContext:
    environment: ActionEnvironment
    user: ContextUser
    params: SerializableRecord
    organization: OrganizationDef
    page: PageInfo


class StartTransactionInputs(BaseModel):
    transaction_id: str
    action: ActionInfo
    environment: ActionEnvironment
    user: ContextUser
    params: SerializableRecord


class OpenPageInputs(BaseModel):
    page_key: str
    client_id: Optional[str] = None
    page: PageInfo
    environment: ActionEnvironment
    user: ContextUser
    params: SerializableRecord


class OpenPageReturnsSuccess(BaseModel):
    type: Literal["SUCCESS"] = "SUCCESS"
    page_key: str


class OpenPageReturnsError(BaseModel):
    type: Literal["ERROR"] = "ERROR"
    message: Optional[str] = None


OpenPageReturns = Annotated[
    Union[OpenPageReturnsSuccess, OpenPageReturnsError],
    Field(discriminator="type"),
]


class ClosePageInputs(BaseModel):
    page_key: str


HostSchemaMethodName = Literal[
    "IO_RESPONSE",
    "START_TRANSACTION",
    "OPEN_PAGE",
    "CLOSE_PAGE",
]
HostSchema = dict[HostSchemaMethodName, RPCMethod]

host_schema: HostSchema = {
    "IO_RESPONSE": RPCMethod(
        inputs=IOResponseInputs,
        returns=None,
    ),
    "START_TRANSACTION": RPCMethod(
        inputs=StartTransactionInputs,
        returns=None,
    ),
    "OPEN_PAGE": RPCMethod(
        inputs=OpenPageInputs,
        returns=OpenPageReturns,
    ),
    "CLOSE_PAGE": RPCMethod(
        inputs=ClosePageInputs,
        returns=None,
    ),
}

AnyRPCSchemaMethodName: TypeAlias = Union[
    WSServerSchemaMethodName, ClientSchemaMethodName, HostSchemaMethodName
]

RPCSchemaMethodName = TypeVar(
    "RPCSchemaMethodName",
    bound=AnyRPCSchemaMethodName,
)


class DuplexMessage(GenericModel, Generic[RPCSchemaMethodName]):
    id: str
    method_name: RPCSchemaMethodName
    data: Any
    kind: Literal["CALL", "RESPONSE"]
