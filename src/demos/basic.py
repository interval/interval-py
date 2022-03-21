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
    message = await io.group([io.input.text("Hello!", help_text="From python!")])

    print(message)

    return {"message": message[0]}


@interval.action_with_slug("add-two-numbers")
async def add_two_numbers(io: IO):
    n1 = await io.input.number("First number")
    n2 = await io.input.number("Second number")

    print("sum", n1 + n2)

    return {"sum": n1 + n2, "from": "🐍"}


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
