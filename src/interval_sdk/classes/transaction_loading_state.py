from typing import Awaitable, Callable, TypeAlias

from .logger import Logger
from ..types import BaseModel


class LoadingState(BaseModel):
    title: str | None = None
    description: str | None = None
    items_in_queue: int | None = None
    items_completed: int | None = None


class TransactionLoadingState:
    Sender: TypeAlias = Callable[[LoadingState], Awaitable[None]]

    _logger: Logger
    _sender: Sender
    _state: LoadingState | None = None

    def __init__(self, logger: Logger, sender: Sender):
        self._logger = logger
        self._sender = sender

    async def _send_state(self):
        # TODO: Some kind of batching
        try:
            await self._sender(
                self._state if self._state is not None else LoadingState()
            )
        except Exception as err:
            self._logger.error("Failed sending loading state to Interval")
            self._logger.debug(err)

    @property
    def state(self) -> LoadingState | None:
        if self._state is not None:
            return self._state.copy()

    async def start(
        self,
        title: str | None = None,
        description: str | None = None,
        items_in_queue: int | None = None,
    ):
        self._state = LoadingState()
        if title is not None:
            self._state.title = title
        if description is not None:
            self._state.description = description
        if items_in_queue is not None:
            self._state.items_in_queue = items_in_queue
            self._state.items_completed = 0

        return await self._send_state()

    async def update(
        self,
        title: str | None = None,
        description: str | None = None,
        items_in_queue: int | None = None,
    ):
        if self._state is None:
            self._logger.warn("Please call `loading.start` before `loading.update`")
            return await self.start(
                title=title,
                description=description,
                items_in_queue=items_in_queue,
            )

        if title is not None:
            self._state.title = title
        if description is not None:
            self._state.description = description
        if items_in_queue is not None:
            self._state.items_in_queue = items_in_queue
            if self._state.items_completed is None:
                self._state.items_completed = 0

        return await self._send_state()

    async def complete_one(self):
        if self._state is None or self._state.items_in_queue is None:
            self._logger.warn(
                "Pleaes call `loading.start` with `items_in_queue` before `loading.complete_one`, nothing to complete."
            )
            return

        if self._state.items_completed is None:
            self._state.items_completed = 0

        self._state.items_completed += 1
        return await self._send_state()
