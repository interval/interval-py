import asyncio, signal, sys
from typing import Optional

from interval_sdk import Interval, IO, ActionContext

interval = Interval(
    "live_N47qd1BrOMApNPmVd0BiDZQRLkocfdJKzvt8W6JT5ICemrAN",
    endpoint="ws://localhost:3000/websocket",
    log_level="debug",
)


@interval.action
async def wait_a_while(_: IO, ctx: ActionContext):
    await ctx.loading.start("Waiting")
    await asyncio.sleep(5)
    return "Done!"


loop = asyncio.get_event_loop()
task = loop.create_task(interval.listen_async())

close_task: Optional[asyncio.Task[None]] = None


async def handle_close_inner():
    try:
        print("Closing...")
        await interval.gracefully_shutdown()
        print("Closed!")
    except Exception as err:
        print("Failed closing gracefully", file=sys.stderr)
        print("Closing forcibly")
        await interval.close()


def stop_loop(fut: asyncio.Future[None]):
    fut.result()
    loop.stop()


def handle_close():
    global close_task

    if close_task is not None:
        return

    close_task = loop.create_task(handle_close_inner())
    close_task.add_done_callback(stop_loop)


loop.add_signal_handler(signal.SIGINT, handle_close)

loop.run_forever()
