from dataclasses import dataclass as base_dataclass
from typing import Any, Generic, Optional, Type, TypeAlias, Literal, TypeVar, TypedDict
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
    type: Literal["success"]
    environment: ActionEnvironment
    invalid_slugs: list[str]
    organization: OrganizationDef
    dashboard_url: str
    sdk_alert: SdkAlert | None = None
    warnings: list[str]


class InitializeHostReturnsError(BaseModel):
    type: Literal["error"]
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
    type: Literal["success"]
    id: str


class EnqueueActionReturnsError(BaseModel):
    type: Literal["error"]
    message: str


EnqueueActionReturns = Annotated[
    EnqueueActionReturnsSuccess | EnqueueActionReturnsError,
    Field(discriminator="type"),
]


class DequeueActionInputs(BaseModel):
    id: str


class DequeueActionReturnsSuccess(BaseModel):
    type: Literal["success"]
    id: str
    assignee: str | None
    params: SerializableRecord | None


class DequeueActionReturnsError(BaseModel):
    type: Literal["error"]
    message: str


DequeueActionReturns = Annotated[
    DequeueActionReturnsSuccess | DequeueActionReturnsError,
    Field(discriminator="type"),
]

WSServerSchemaMethodName = Literal[
    "CONNECT_TO_TRANSACTION_AS_CLIENT",
    "RESPOND_TO_IO_CALL",
    "SEND_IO_CALL",
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


@dataclass
class ActionContext:
    environment: ActionEnvironment
    user: ContextUser
    params: SerializableRecord
    organization: OrganizationDef
    action: ActionInfo


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


class StartTransactionInputs(ActionContext):
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
    type: Literal["SUCCESS"]
    page_key: str


class OpenPageReturnsError(BaseModel):
    type: Literal["ERROR"]
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
