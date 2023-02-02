import asyncio, signal
from interval_sdk import Interval, IO

interval = Interval(
    api_key="alex_dev_kcLjzxNFxmGLf0aKtLVhuckt6sziQJtxFOdtM19tBrMUp5mj",
    endpoint="ws://localhost:3000/websocket",
)


@interval.action
async def hello_world(io: IO):
    name = await io.input.text("Your name")
    return f"Hello, {name}!"


loop = asyncio.get_event_loop()


async def handle_request(_reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    writer.write("OK".encode("utf-8"))
    await writer.drain()
    writer.close()


async def create_server():
    # Google Cloud Run requires a process listening on port 8080
    server = await asyncio.start_server(handle_request, port=4040)
    await server.serve_forever()


# Handle interrupt signals
for sig in {signal.SIGINT, signal.SIGTERM}:
    loop.add_signal_handler(sig, loop.stop)

fut = asyncio.gather(
    interval.listen_async(),
    create_server(),
)

loop.run_forever()
