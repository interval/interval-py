import asyncio
from asyncio import Future
from dataclasses import dataclass
from typing import Any, Callable, Optional
from uuid import UUID, uuid4


from typing_extensions import Literal, Awaitable
import websockets, websockets.client, websockets.exceptions
from pydantic import BaseModel

from .logger import LogLevel, Logger
from ..types import IntervalError


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
    _logger: Logger
    _ws: websockets.client.WebSocketClientProtocol
    _send_timeout: float
    _ping_timeout: float
    _connect_timeout: float
    _is_authenticated: bool = False

    id: UUID
    on_message: Optional[Callable[[str], Awaitable[None]]]
    on_open: Optional[Callable[[], Awaitable[None]]]
    on_error: Optional[Callable[[Exception], Awaitable[None]]]
    on_close: Optional[Callable[[int, str], Awaitable[None]]]
    on_authenticated: Future[None]

    _out_queue: asyncio.Queue[Message]
    _pending_messages: dict[UUID, PendingMessage]
    _message_tasks: set[asyncio.Task]
    _connection_future: Optional[Future]
    _num_producers: int

    def __init__(
        self,
        ws: websockets.client.WebSocketClientProtocol,
        id: Optional[UUID] = None,
        send_timeout: float = 5,
        ping_timeout: float = 5,
        connect_timeout: float = 10,
        on_message: Optional[Callable[[str], Awaitable[None]]] = None,
        on_open: Optional[Callable[[], Awaitable[None]]] = None,
        on_error: Optional[Callable[[Exception], Awaitable[None]]] = None,
        on_close: Optional[Callable[[int, str], Awaitable[None]]] = None,
        log_level: Optional[LogLevel] = None,
        num_producers: int = 1,
    ):
        self._logger = Logger(log_level=log_level, prefix=self.__class__.__name__)
        self._ws = ws
        self.id = id if id is not None else uuid4()
        self._send_timeout = send_timeout
        self._connect_timeout = connect_timeout
        self._ping_timeout = ping_timeout

        self.on_message = on_message
        self.on_open = on_open
        self.on_error = on_error
        self.on_close = on_close

        self._out_queue = asyncio.Queue()
        self._pending_messages = {}
        self._message_tasks = set()
        self._num_producers = num_producers

    @property
    def is_open(self) -> bool:
        return self._ws.open

    async def connect(self) -> None:
        if self.is_open and self._is_authenticated:
            return

        if self.on_open:
            await self.on_open()

        loop = asyncio.get_running_loop()
        self.on_authenticated = loop.create_future()

        self._connection_future = asyncio.gather(
            # websockets can only have one consumer I think
            self._consumer_handler(self._ws),
            *(self._producer_handler(self._ws) for _ in range(self._num_producers)),
        )

        def on_complete(fut: Future):
            try:
                fut.result()
            except asyncio.CancelledError:
                pass
            except BaseException as err:
                self._logger.error("Encountered connection loop error")
                self._logger.print_exception(err)

            self._connection_future = None

        self._connection_future.add_done_callback(on_complete)
        await asyncio.wait_for(self.on_authenticated, self._connect_timeout)

    async def _consumer_handler(
        self, ws: websockets.client.WebSocketClientProtocol
    ) -> None:
        loop = asyncio.get_running_loop()
        try:
            async for message in ws:
                meta = Message.parse_raw(message)

                if meta.type == "ACK":
                    pm = self._pending_messages.pop(meta.id)
                    if not pm.on_ack_received.done():
                        pm.on_ack_received.set_result(None)
                elif meta.type == "MESSAGE":
                    await self._out_queue.put(
                        Message(id=meta.id, data=None, type="ACK")
                    )
                    if meta.data == "authenticated":
                        self._is_authenticated = True
                        self.on_authenticated.set_result(None)
                        continue

                    task = loop.create_task(self._handle_message(meta.data))

                    def on_complete(task: asyncio.Task):
                        try:
                            task.result()
                        except (
                            TimeoutError,
                            asyncio.CancelledError,
                            IntervalError,
                            IOError,
                        ) as err:
                            self._logger.print_exception(err)
                            pass
                        except BaseException as err:
                            self._logger.error("Error sending message", err)
                            self._logger.print_exception(err)
                        finally:
                            self._message_tasks.remove(task)

                    task.add_done_callback(on_complete)
                    self._message_tasks.add(task)
        except websockets.exceptions.ConnectionClosed as e:
            await self._handle_close(e.code, e.reason)
        except Exception as e:
            self._logger.error("Error in consumer handler", e)
            self._logger.print_exception(e)

    async def _handle_message(self, message: str):
        if not self.is_open:
            return

        if self.on_message is not None:
            await self.on_message(message)

    async def _producer_handler(
        self, ws: websockets.client.WebSocketClientProtocol
    ) -> None:

        while True:
            try:
                message = await self._out_queue.get()
                try:
                    await ws.send(message.json(by_alias=True))
                except websockets.exceptions.ConnectionClosed as e:
                    await self._handle_close(e.code, e.reason)
                except asyncio.exceptions.TimeoutError:
                    # No need to put back in queue, we'll try resending again
                    pass
                except Exception as e:
                    self._logger.error("Error in producer handler", e)
                    self._logger.print_exception(e)
                finally:
                    self._out_queue.task_done()
            except Exception as e:
                self._logger.error("Error getting message from queue?", e)
                self._logger.print_exception(e)

    async def send(self, data: str, *, timeout_factor: Optional[int] = None) -> None:
        if not self.is_open:
            raise NotConnectedError

        if timeout_factor is None:
            timeout_factor = 1

        loop = asyncio.get_running_loop()

        id = uuid4()
        fut = loop.create_future()
        message = Message(id=id, data=data, type="MESSAGE")
        self._pending_messages[message.id] = PendingMessage(
            message=message, on_ack_received=fut
        )
        await self._out_queue.put(message)

        await asyncio.wait_for(fut, self._send_timeout * timeout_factor)

    async def _handle_close(self, code: int, reason: str):
        if not self.on_authenticated.done():
            self.on_authenticated.cancel()

        if self._connection_future is not None:
            self._connection_future.cancel()

        if self._ws is not None:
            await self._ws.close()

        if self.on_close:
            await self.on_close(code, reason)

    async def close(self, code: int = 1000, reason: str = "Closed by client") -> None:
        await self._handle_close(code, reason)

    async def ping(self) -> None:
        if not self.is_open:
            raise NotConnectedError

        if self._ws is None:
            raise NotConnectedError

        # start the ping
        waiter = await self._ws.ping()

        # wait for the response
        response = await asyncio.wait_for(waiter, self._ping_timeout)

        return response
