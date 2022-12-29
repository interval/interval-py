from dataclasses import dataclass as base_dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    Type,
    TypeAlias,
    Literal,
    TypeVar,
    TypedDict,
)
from typing_extensions import Annotated

from pydantic import Field
from pydantic.dataclasses import dataclass

from .util import SerializableRecord
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


class LoadingState(BaseModel):
    title: str | None = None
    description: str | None = None
    items_in_queue: int | None = None
    items_completed: int | None = None


class SendLoadingCallInputs(LoadingState):
    transaction_id: str
    label: str | None = None


class SendLogInputs(BaseModel):
    transaction_id: str
    data: str
    index: int | None = None
    timestamp: int | None = None


@dataclass
class DeliveryInstruction:
    to: str
    method: Literal["EMAIL", "SLACK"] | None = None


class NotifyInputs(BaseModel):
    transaction_id: str
    message: str
    title: str | None = None
    idempotency_key: str | None = None
    delivery_instructions: list[DeliveryInstruction] | None = None
    created_at: str


class SendRedirectInputs(BaseModel):
    transaction_id: str
    url: str | None = None
    route: str | None = None
    params: SerializableRecord | None = None


class MarkTransactionCompleteInputs(BaseModel):
    transaction_id: str
    result: Optional[str]


class AccessControlObjectDefinition(TypedDict):
    teams: list[str]


AccessControlDefinition: TypeAlias = (
    Literal["entire-organization"] | AccessControlObjectDefinition
)


class SdkAlert(BaseModel):
    min_sdk_version: str
    severity: Literal["INFO", "WARNING", "ERROR"]
    message: str | None = None


class ActionDefinition(BaseModel):
    group_slug: str | None = None
    slug: str
    name: str | None = None
    description: str | None = None
    backgroundable: bool = False
    unlisted: bool = False
    access: AccessControlDefinition | None = None


class PageDefinition(BaseModel):
    slug: str
    name: str
    description: str | None = None
    has_handler: bool = False
    unlisted: bool = False
    access: AccessControlDefinition | None = None


class InitializeHostInputs(BaseModel):
    api_key: str
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
    sdk_alert: SdkAlert | None = None
    warnings: list[str]


class InitializeHostReturnsError(BaseModel):
    type: Literal["error"] = "error"
    message: str
    sdk_alert: SdkAlert | None = None


InitializeHostReturns = Annotated[
    InitializeHostReturnsSuccess | InitializeHostReturnsError,
    Field(discriminator="type"),
]


class EnqueueActionInputs(BaseModel):
    slug: str
    assignee: str | None
    params: SerializableRecord | None


class EnqueueActionReturnsSuccess(BaseModel):
    type: Literal["success"] = "success"
    id: str


class EnqueueActionReturnsError(BaseModel):
    type: Literal["error"] = "error"
    message: str


EnqueueActionReturns = Annotated[
    EnqueueActionReturnsSuccess | EnqueueActionReturnsError,
    Field(discriminator="type"),
]


class DequeueActionInputs(BaseModel):
    id: str


class DequeueActionReturnsSuccess(BaseModel):
    type: Literal["success"] = "success"
    id: str
    assignee: str | None
    params: SerializableRecord | None


class DequeueActionReturnsError(BaseModel):
    type: Literal["error"] = "error"
    message: str


DequeueActionReturns = Annotated[
    DequeueActionReturnsSuccess | DequeueActionReturnsError,
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
    first_name: str | None = None
    last_name: str | None = None


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

    _transaction_id: str
    _send_log: Callable[..., Awaitable[None]]
    _log_index = 0

    def __init__(
        self,
        transaction_id: str,
        environment: ActionEnvironment,
        user: ContextUser,
        params: SerializableRecord,
        organization: OrganizationDef,
        action: ActionInfo,
        send_log: Callable[..., Awaitable[None]],
    ):
        self._transaction_id = transaction_id
        self._send_log = send_log

        self.environment = environment
        self.user = user
        self.params = params
        self.organization = organization
        self.action = action

    async def log(self, *args):
        self._log_index += 1
        await self._send_log(
            self._transaction_id,
            self._log_index,
            *args,
        )


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
    client_id: str | None = None
    page: PageInfo
    environment: ActionEnvironment
    user: ContextUser
    params: SerializableRecord


class OpenPageReturnsSuccess(BaseModel):
    type: Literal["SUCCESS"] = "SUCCESS"
    page_key: str


class OpenPageReturnsError(BaseModel):
    type: Literal["ERROR"] = "ERROR"
    message: str | None = None


OpenPageReturns = Annotated[
    OpenPageReturnsSuccess | OpenPageReturnsError,
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

AnyRPCSchemaMethodName: TypeAlias = (
    WSServerSchemaMethodName | ClientSchemaMethodName | HostSchemaMethodName
)

RPCSchemaMethodName = TypeVar(
    "RPCSchemaMethodName",
    bound=AnyRPCSchemaMethodName,
)


class DuplexMessage(GenericModel, Generic[RPCSchemaMethodName]):
    id: str
    method_name: RPCSchemaMethodName
    data: Any
    kind: Literal["CALL", "RESPONSE"]
