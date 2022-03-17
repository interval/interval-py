import asyncio
from interval_py import Interval, IO

interval = Interval(
    "alex_dev_kcLjzxNFxmGLf0aKtLVhuckt6sziQJtxFOdtM19tBrMUp5mj",
    endpoint="ws://localhost:3002",
)


@interval.action
async def add_a_number(io: IO, _):
    await io.input.text("ok", help_text="ok")


@interval.action_with_slug("add-two-numbers")
async def add_two_numbers(io: IO, _):
    await io.input.text("ok", help_text="ok")


asyncio.run(interval.listen())
