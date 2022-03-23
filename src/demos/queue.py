import asyncio
from datetime import datetime

from interval_sdk import Interval, IO, ActionContext

interval = Interval(
    "alex_dev_kcLjzxNFxmGLf0aKtLVhuckt6sziQJtxFOdtM19tBrMUp5mj",
    endpoint="ws://localhost:3002",
    log_level="debug",
)


@interval.action
async def echo_context(_: IO, ctx: ActionContext):
    print(ctx)
    return {
        "user": f"{ctx.user.first_name} {ctx.user.last_name}",
        "environment": ctx.environment,
        **ctx.params,
    }


loop = asyncio.new_event_loop()
task = loop.create_task(interval.listen_async())


async def queue():
    await asyncio.sleep(1)
    await interval.actions.enqueue(
        "echo_context",
        params={
            "true": True,
            "false": False,
            "number": 1337,
            "string": "string",
            "date": datetime.now(),
            "none": None,
        },
    )

    await interval.actions.enqueue(
        "echo_context",
        assignee_email="alex@interval.com",
        params={
            "message": "Hello, queue!",
        },
    )

    queued_action = await interval.actions.enqueue(
        "echo_context", params={"message": "Hello, anyone!"}
    )

    await interval.actions.dequeue(queued_action.id)


loop.create_task(queue())


loop.run_forever()
