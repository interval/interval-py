from datetime import datetime

from interval_py import Interval, IO

interval = Interval(
    "alex_dev_kcLjzxNFxmGLf0aKtLVhuckt6sziQJtxFOdtM19tBrMUp5mj",
    endpoint="ws://localhost:3002",
    log_level="debug",
)


@interval.action
async def hello_interval():
    return {"hello": "from python!"}


@interval.action
async def echo_message(io: IO):
    [message] = await io.group(io.input.text("Hello!", help_text="From python!"))

    return {"message": message}


@interval.action
async def io_display_heading(io: IO):
    await io.display.heading("io.display.heading result")


@interval.action_with_slug("add-two-numbers")
async def add_two_numbers(io: IO):
    n1 = await io.input.number("First number")
    n2 = await io.input.number(
        "Second number", min=n1, help_text=f"Must be greater than {n1}"
    )

    print("sum", n1 + n2)

    return {"sum": n1 + n2, "from": "🐍"}


@interval.action_with_slug("io.display.object")
async def io_display_object(io: IO):
    await io.group(
        io.display.object(
            "Here's an object",
            data={
                "isTrue": True,
                "isFalse": False,
                "number": 15,
                "none_value": None,
                "nested": {
                    "name": "Interval",
                },
                "longList": [f"Item {i}" for i in range(100)],
                "date": datetime.now(),
            },
        )
    )


@interval.action
async def spreadsheet_test(io: IO):
    sheet = await io.input.spreadsheet(
        "Add a spreadsheet",
        columns={
            "firstName": "string",
            "last_name": "string",
            "age": "number?",
        },
    )

    print(sheet)


interval.listen()
