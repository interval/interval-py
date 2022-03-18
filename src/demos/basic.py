import asyncio
from interval_py import Interval, IO


def main():
    interval = Interval(
        "alex_dev_kcLjzxNFxmGLf0aKtLVhuckt6sziQJtxFOdtM19tBrMUp5mj",
        endpoint="ws://localhost:3002",
        log_level="debug",
    )

    @interval.action
    async def hello_interval(io: IO, _):
        return {"hello": "from python!"}

    @interval.action
    async def add_a_number(io: IO, _):
        message = await io.input.text("Hello!", help_text="From python!")

        return {"message": message}

    @interval.action_with_slug("add-two-numbers")
    async def add_two_numbers(io: IO, _):
        n1 = int(await io.input.text("First number"))
        print("n1", n1)
        n2 = int(await io.input.text("Second number"))

        print("sum", n1 + n2)

        return {"sum": n1 + n2, "from": "🐍"}

    interval.listen()

    # loop = asyncio.get_event_loop()
    # f1: asyncio.Future[str] = loop.create_future()
    # f2: asyncio.Future[int] = loop.create_future()
    #
    # f = asyncio.gather(f1, f2)


if __name__ == "__main__":
    main()
