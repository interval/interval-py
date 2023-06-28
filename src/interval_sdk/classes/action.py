from dataclasses import dataclass
from typing import Optional

from interval_sdk.handlers import IntervalActionHandler

from ..internal_rpc_schema import AccessControlDefinition


@dataclass
class Action:
    handler: IntervalActionHandler
    name: Optional[str] = None
    description: Optional[str] = None
    backgroundable: bool = False
    warn_on_close: bool = True
    unlisted: bool = False
    access: Optional[AccessControlDefinition] = None
