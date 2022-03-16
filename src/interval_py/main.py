from typing import Optional, TypeAlias, Callable, Awaitable

from .io_schema import IOFunctionReturnType
from .io_client import Logger, LogLevel
from .io import IO

IntervalActionHandler: TypeAlias = Callable[[IO], Awaitable[IOFunctionReturnType]]


class Interval:
    _logger: Logger
    _endpoint: str = "wss://intervalkit.com/websocket"
    _api_key: str
    _actions: dict[str, IntervalActionHandler]

    def __init__(
        self, api_key: str, endpoint: Optional[str] = None, log_level: LogLevel = "prod"
    ):
        self._api_key = api_key
        if endpoint is not None:
            self._endpoint = endpoint

        self._actions = {}
        self._logger = Logger(log_level)

    def action(self, action_callback: IntervalActionHandler):
        self._add_action(action_callback.__name__, action_callback)

    def action_with_slug(self, slug: str):
        def action_adder(action_callback: IntervalActionHandler):
            self._add_action(slug, action_callback)

        return action_adder

    def _add_action(self, slug: str, action_callback: IntervalActionHandler):
        self._actions[slug] = action_callback

    def listen(self):
        print(self._actions)
