from pydantic.dataclasses import dataclass

from interval_sdk.handlers import IntervalActionHandler

from ..internal_rpc_schema import AccessControlDefinition, ActionDefinition


@dataclass
class Action:
    name: str | None = None
    description: str | None = None
    handler: IntervalActionHandler
    backgroundable = False
    unlisted = False
    access: AccessControlDefinition | None = None
