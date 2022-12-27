from dataclasses import dataclass

from interval_sdk.handlers import IntervalActionHandler

from ..internal_rpc_schema import AccessControlDefinition, ActionDefinition


@dataclass
class Action:
    handler: IntervalActionHandler
    name: str | None = None
    description: str | None = None
    backgroundable = False
    unlisted = False
    access: AccessControlDefinition | None = None
