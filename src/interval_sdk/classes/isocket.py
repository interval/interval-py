import asyncio, sys
from asyncio.futures import Future
from dataclasses import dataclass
from typing import Any, Callable, Literal, Awaitable
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
    _ws: websockets.client.WebSocketClientProtocol
    _send_timeout: float
    _connect_timeout: float
    _ping_timeout: float
    _is_authenticated: bool

    id: UUID
    on_message: Callable[[str], Awaitable[None]] | None
    on_open: Callable[[], Awaitable[None]] | None
    on_error: Callable[[Exception], Awaitable[None]] | None
    on_close: Callable[[int, str], Awaitable[None]] | None
    on_authenticated: Future[None]
    is_closed: bool

    _out_queue: asyncio.Queue[Message] = asyncio.Queue()
    _pending_messages: dict[UUID, PendingMessage] = {}
    _connection_future: Future | None

    def __init__(
        self,
        ws: websockets.client.WebSocketClientProtocol,
        id: UUID = uuid4(),
        send_timeout: float = 3,
        connect_timeout: float = 10,
        ping_timeout: float = 3,
        on_message: Callable[[str], Awaitable[None]] | None = None,
        on_open: Callable[[], Awaitable[None]] | None = None,
        on_error: Callable[[Exception], Awaitable[None]] | None = None,
        on_close: Callable[[int, str], Awaitable[None]] | None = None,
    ):
        self._ws = ws
        self.id = id
        self._send_timeout = send_timeout
        self._connect_timeout = connect_timeout
        self._ping_timeout = ping_timeout
        self.is_closed = False

        self.on_message = on_message
        self.on_open = on_open
        self.on_error = on_error
        self.on_close = on_close

    async def connect(self) -> None:
        if self.on_open:
            await self.on_open()

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.on_authenticated = fut

        self._connection_future = asyncio.gather(
            self._consumer_handler(self._ws),
            self._producer_handler(self._ws),
        )
        await asyncio.wait_for(fut, self._connect_timeout)

    async def _consumer_handler(
        self, ws: websockets.client.WebSocketClientProtocol
    ) -> None:
        try:
            async for message in ws:
                meta = Message.parse_raw(message)

                if meta.type == "ACK":
                    pm = self._pending_messages.get(meta.id, None)
                    if pm:
                        pm.on_ack_received.set_result(None)
                        self._pending_messages.pop(meta.id)
                elif meta.type == "MESSAGE":
                    await self._out_queue.put(
                        Message(id=meta.id, data=None, type="ACK")
                    )
                    if meta.data == "authenticated":
                        self._is_authenticated = True
                        self.on_authenticated.set_result(None)
                        continue

                    if self.on_message:
                        asyncio.ensure_future(self.on_message(meta.data))
        except websockets.exceptions.ConnectionClosed as e:
            if self.on_close:
                await self.on_close(e.code, e.reason)
        except Exception as e:
            print("Error in consumer handler", e, file=sys.stderr)

    async def _producer_handler(
        self, ws: websockets.client.WebSocketClientProtocol
    ) -> None:

        while True:
            message = await self._out_queue.get()
            try:
                await ws.send(message.json())
                self._out_queue.task_done()
            except websockets.exceptions.ConnectionClosed as e:
                if self.on_close:
                    await self.on_close(e.code, e.reason)
            except asyncio.exceptions.TimeoutError:
                # No need to put back in queue, we'll try resending again
                pass
            except Exception as e:
                print("Error in producer handler", e, file=sys.stderr)

    async def send(self, data: str) -> None:
        if self._ws is None:
            raise NotConnectedError

        loop = asyncio.get_running_loop()

        id = uuid4()
        fut = loop.create_future()
        message = Message(id=id, data=data, type="MESSAGE")
        self._pending_messages[message.id] = PendingMessage(
            message=message, on_ack_received=fut
        )
        await self._out_queue.put(message)

        await asyncio.wait_for(fut, self._send_timeout)

    async def close(self) -> None:
        self.is_closed = True

        if self._connection_future is not None:
            self._connection_future.cancel()

        if self._ws is not None:
            await self._ws.close()

        if self.on_close:
            await self.on_close(1000, "Closed by client")

    async def ping(self) -> None:
        if self.is_closed:
            raise NotConnectedError

        if self._ws is None:
            raise NotConnectedError

        loop = asyncio.get_running_loop()

        id = uuid4()
        fut = loop.create_future()
        message = Message(id=id, data="ping", type="MESSAGE")
        self._pending_messages[message.id] = PendingMessage(
            message=message, on_ack_received=fut
        )
        await self._out_queue.put(message)

        await asyncio.wait_for(fut, self._ping_timeout)
