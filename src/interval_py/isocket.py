import asyncio, json
from asyncio.futures import Future
from dataclasses import dataclass
from typing import Any, Callable, Optional, Literal, Awaitable
from uuid import UUID, uuid4


import websockets, websockets.client, websockets.exceptions
from pydantic import BaseModel


class Message(BaseModel):
    data: Any
    id: UUID
    type: Literal["ACK", "MESSAGE"]


@dataclass
class PendingMessage:
    on_ack_received: Future[None]
    message: Message


class NotConnectedError(Exception):
    pass


class ISocket:
    _endpoint: str
    _ws: websockets.client.WebSocketClientProtocol | None
    _connect_timeout: float
    _send_timeout: float
    _is_authenticated: bool

    id: UUID
    on_message: Callable[[str], Awaitable[None]] | None
    on_open: Callable[[], Awaitable[None]] | None
    on_error: Callable[[Exception], Awaitable[None]] | None
    on_close: Callable[[int, str], Awaitable[None]] | None
    on_authenticated: Callable[[], Awaitable[None]] | None

    _out_queue: asyncio.Queue[Message]
    _pending_messages: dict[UUID, PendingMessage]

    def __init__(
        self,
        endpoint: str,
        id: UUID = uuid4(),
        connect_timeout: float = 15,
        send_timeout: float = 3,
        on_message: Callable[[str], Awaitable[None]] | None = None,
        on_open: Callable[[], Awaitable[None]] | None = None,
        on_error: Callable[[Exception], Awaitable[None]] | None = None,
        on_close: Callable[[int, str], Awaitable[None]] | None = None,
        on_authenticated: Callable[[], Awaitable[None]] | None = None,
    ):
        self._endpoint = endpoint
        self.id = id
        self._connect_timeout = connect_timeout
        self._send_timeout = send_timeout

        self.on_message = on_message
        self.on_open = on_open
        self.on_error = on_error
        self.on_close = on_close
        self.on_authenticated = on_authenticated

    async def connect(self) -> None:
        self._ws = await websockets.client.connect(
            self._endpoint, open_timeout=self._connect_timeout
        )

        if self.on_open:
            self.on_open()

        try:
            await asyncio.gather(
                self._consumer_handler(self._ws),
                self._producer_handler(self._ws),
            )
        except websockets.exceptions.ConnectionClosed as e:
            if self.on_close:
                self.on_close(e.code, e.reason)

    async def _consumer_handler(
        self, ws: websockets.client.WebSocketClientProtocol
    ) -> None:
        async for message in ws:
            data = json.loads(message)
            meta = Message.parse_obj(data)

            if meta.type == "ACK":
                pm = self._pending_messages.get(meta.id)
                if pm:
                    pm.on_ack_received.set_result(None)
                    self._pending_messages.pop(meta.id)
            elif meta.type == "MESSAGE":
                await self._out_queue.put(Message(id=meta.id, data=None, type="ACK"))
                if meta.data == "authenticated":
                    self._is_authenticated = True
                    if self.on_authenticated:
                        self.on_authenticated()
                    return

                if self.on_message:
                    self.on_message(meta.data)

    async def _producer_handler(
        self, ws: websockets.client.WebSocketClientProtocol
    ) -> None:

        while True:
            message = await self._out_queue.get()
            await ws.send(json.dumps(message))

    async def send(self, data: str) -> None:
        if self._ws is None:
            raise NotConnectedError

        loop = asyncio.get_event_loop()

        id = uuid4()
        fut = loop.create_future()
        message = Message(id=id, data=data, type="MESSAGE")
        self._pending_messages[message.id] = PendingMessage(
            message=message, on_ack_received=fut
        )

        await asyncio.wait_for(fut, self._send_timeout)

    async def close(self):
        if self._ws is None:
            raise NotConnectedError

        await self._ws.close()
