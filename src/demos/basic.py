from datetime import datetime

from interval_sdk import Interval, IO

interval = Interval(
    "alex_dev_kcLjzxNFxmGLf0aKtLVhuckt6sziQJtxFOdtM19tBrMUp5mj",
    endpoint="ws://localhost:3000/websocket",
    log_level="debug",
)


@interval.action
async def hello_interval():
    return {"hello": "from python!"}


@interval.action
async def throw_error():
    raise Exception("Error!")


@interval.action
async def echo_message(io: IO):
    [message] = await io.group(io.input.text("Hello!", help_text="From python!"))

    return {"message": message}


@interval.action
async def io_display_heading(io: IO):
    await io.display.heading("io.display.heading result")


@interval.action
async def io_display_image(io: IO):
    await io.display.image(
        "A nice pic",
        url="https://media.discordapp.net/attachments/1011355905490694355/1030870113324367943/unknown.png",
        size="large",
    )


@interval.action_with_slug("add-two-numbers")
async def add_two_numbers(io: IO):
    n1 = await io.input.number("First number")
    n2 = await io.input.number(
        "Second number",
        min=n1,
        decimals=2,
        help_text=f"Must be greater than {n1}",
    )

    print("sum", n1 + n2)

    return {"n1": n1, "n2": n2, "sum": n1 + n2, "from": "🐍"}


@interval.action_with_slug("io.display.code")
async def io_display_code(io: IO):
    await io.group(
        io.display.code(
            "Some python",
            code="""from datetime import datetime

print("Hello from python!")
print(datetime.now())""",
        ),
        io.display.code(
            "Some typescript",
            code="""const logTime = () => {
  const time = new Date().toLocaleTimeString()
  console.log(time)
}

setInterval(logTime, 1000)""",
            language="typescript",
        ),
    )

    return "All done!"


@interval.action_with_slug("io.display.video")
async def io_display_video(io: IO):
    await io.display.video(
        "Video via url",
        url="https://upload.wikimedia.org/wikipedia/commons/a/ad/The_Kid_scenes.ogv",
        size="large",
    )
    return "All done!"


@interval.action_with_slug("io.input.url")
async def io_input_url(io: IO):
    url, opt_url = await io.group(
        io.input.url("One URL please"),
        io.input.url("A URL, if you want").optional(),
    )

    print("url", url)
    print("opt_url", opt_url)

    return {"url": str(url), "opt_url": str(opt_url)}


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
                "date": datetime.now().date(),
                "time": datetime.now().time(),
                "datetime": datetime.now(),
            },
        )
    )


@interval.action
async def spreadsheet_test(io: IO):
    sheet = await io.experimental.spreadsheet(
        "Add a spreadsheet",
        columns={
            "firstName": "string",
            "last_name": "string",
            "age": "number?",
        },
    )

    print(sheet)


@interval.action
async def table_test(io: IO):
    data = [
        {"a": i, "b": 2 * i, "c": 3 * i, "d": [i, i, i], "e": {"i": i}}
        for i in range(100)
    ]

    await io.display.table(
        "Table",
        data=data,
    )

    selected = await io.select.table(
        "Select table",
        data=data,
        columns=[
            {"label": "A", "render": lambda row: row["a"]},
            {
                "label": "B",
                "render": lambda row: {
                    "value": row["b"],
                    "label": f"Item {row['b']}",
                    "href": f"https://example.com/{row['b']}",
                },
            },
        ],
    )

    print(selected)


@interval.action
async def confirm(io: IO):
    confirmed = await io.confirm("Does this work?", help_text="I hope so...")
    return {"confirmed": confirmed}


@interval.action
async def dates(io: IO):
    now = datetime.now()
    [d, t, dt, _] = await io.group(
        io.input.date("Enter a date", default_value=now.date()),
        io.input.time("Enter a time", default_value=now.time()),
        io.input.datetime("Enter a datetime", default_value=now),
        io.input.text("Text input"),
    )

    result = {
        "date": d,
        "time": t,
        "datetime": dt,
    }

    print(result)

    # await io.display.object("Result", data=result)

    return result


@interval.action
async def optional_values(io: IO):
    [name, num, date, color] = await io.group(
        io.input.text("Your name").optional(),
        io.input.number("Pick a number").optional(),
        io.input.date("Enter a date", default_value=datetime.now().date()).optional(),
        io.select.single(
            "Your favorite color",
            options=[
                {
                    "label": "Red",
                    "value": "red",
                },
                {
                    "label": "Blue",
                    "value": "blue",
                },
                {
                    "label": "Orange",
                    "value": "orange",
                },
            ],
        ).optional(),
    )

    print(name, num, date, color)

    return {
        "Name": name if name is not None else "No name selected",
        "Number": num if num is not None else "No number selected",
        "Date": date if date is not None else "No date selected",
        "Favorite color": color["label"] if color is not None else "Unknown",
    }


interval.listen()
