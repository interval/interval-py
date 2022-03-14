from dataclasses import dataclass
from typing import Any, Optional, Type, TypeAlias, Literal

from pydantic import Field
from typing_extensions import Annotated

from .io_schema import SerializableRecord
from .types import BaseModel


class DuplexMessage(BaseModel):
    id: str
    method_name: str
    data: Any
    kind: Literal["CALL", "RESPONSE"]


TRANSACTION_RESULT_SCHEMA_VERSION = 1

ActionEnvironment: TypeAlias = Literal["live", "development"]


@dataclass
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


class InitializeHostInputs(BaseModel):
    api_key: str
    callable_action_names: list[str]
    sdk_name: str
    sdk_version: str


class InitializeHostReturns(BaseModel):
    environment: ActionEnvironment
    invalid_slugs: list[str]
    dashboard_url: str


class EnqueueActionInputs(BaseModel):
    action_name: str
    assignee: str | None
    params: SerializableRecord | None


class EnqueueActionReturnsSuccess(BaseModel):
    type: Literal["success"]
    id: str


class EnqueueActionReturnsError(BaseModel):
    type: Literal["error"]
    message: str


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


WSServerSchemaMethodName = Literal[
    "CONNECT_TO_TRANSACTION_AS_CLIENT",
    "RESPOND_TO_IO_CALL",
    "SEND_IO_CALL",
    "MARK_TRANSACTION_COMPLETE",
    "ENQUEUE_ACTION",
    "DEQUEUE_ACTION",
]

ws_server_schema: dict[WSServerSchemaMethodName, RPCMethod] = {
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
    "ENQUEUE_ACTION": RPCMethod(
        inputs=EnqueueActionInputs,
        returns=Annotated[
            EnqueueActionReturnsSuccess | EnqueueActionReturnsError,
            Field(discriminator="type"),
        ],
    ),
    "DEQUEUE_ACTION": RPCMethod(
        inputs=DequeueActionInputs,
        returns=Annotated[
            DequeueActionReturnsSuccess | DequeueActionReturnsError,
            Field(discriminator="type"),
        ],
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

client_schema: dict[ClientSchemaMethodName, RPCMethod] = {
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
    transactionId: str


class ActionContextUser(BaseModel):
    pass


class ActionContext(BaseModel):
    environment: ActionEnvironment
    user: ActionContextUser
    params: SerializableRecord


class StartTransactionInputs(ActionContext):
    transaction_id: str
    action_name: str


HostSchemaMethodName = Literal["IO_RESPONSE", "START_TRANSACTION"]

host_schema: dict[HostSchemaMethodName, RPCMethod] = {
    "IO_RESPONSE": RPCMethod(
        inputs=IOResponseInputs,
        returns=None,
    ),
    "START_TRANSACTION": RPCMethod(
        inputs=StartTransactionInputs,
        returns=None,
    ),
}
