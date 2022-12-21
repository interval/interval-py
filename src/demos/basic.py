import asyncio
from datetime import date, datetime
from typing import cast
from typing_extensions import NotRequired

from interval_sdk import Interval, IO
from interval_sdk.io_schema import (
    RichSelectOption,
    RenderableSearchResult,
)

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

    return message


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


@interval.action
async def select_single(io: IO):
    class Option(RichSelectOption):
        extraData: NotRequired[bool]

    selected = await io.select.single(
        "Your favorite color",
        options=(
            [
                cast(
                    Option,
                    {
                        "label": "Red",
                        "value": "red",
                    },
                ),
                cast(
                    Option,
                    {
                        "label": "Blue",
                        "value": "blue",
                    },
                ),
                cast(
                    Option,
                    {
                        "label": "Orange",
                        "value": "orange",
                    },
                ),
            ]
        ),
    )

    print(selected)


@interval.action
async def select_multiple(io: IO):
    class Option(RichSelectOption):
        extraData: NotRequired[bool]

    options: list[Option] = [
        {
            "value": date(2022, 6, 20),
            "label": date(2022, 6, 20),
            "extraData": True,
        },
        {
            "value": True,
            "label": True,
        },
        {
            "value": 3,
            "label": 3,
        },
    ]

    selected = await io.select.multiple("Select zero or more", options=options)
    print(selected)

    selected = await io.select.multiple(
        "Optionally modify the selection, selecting between 1 and 2",
        options=options,
        default_value=selected,
        min_selections=1,
        max_selections=2,
    )

    selected_values = [o["value"] for o in selected]

    ret: dict[str, bool] = {}

    for option in options:
        ret[str(option["label"])] = option["value"] in selected_values

    return {
        **ret,
        "extraData": selected[1]["extraData"] if "extraData" in selected[1] else None,
    }


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


@interval.action_with_slug("io.display.link")
async def io_display_link(io: IO):
    await io.display.link(
        "Code",
        action="io.display.code",
        params={"hello": "world"},
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


@interval.action_with_slug("io.display.metadata")
async def io_display_metadata(io: IO):
    await io.display.metadata(
        "User info",
        layout="card",
        data=[
            {"label": "Name", "value": "Alex"},
            {"label": "Email", "value": "alex@interval.com"},
            {"label": "Friends", "value": 24},
        ],
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
            {"label": "A", "renderCell": lambda row: row["a"]},
            {
                "label": "B",
                "renderCell": lambda row: {
                    "value": row["b"],
                    "label": f"Item {row['b']}",
                    "href": f"https://example.com/{row['b']}",
                },
            },
        ],
    )

    print(selected)


@interval.action
async def big_table(io: IO):
    data = [
        {"a": i, "b": 2 * i, "c": 3 * i, "d": [i, i, i], "e": {"i": i}}
        for i in range(100_000)
    ]

    await io.display.table(
        "Table",
        data=data,
    )


@interval.action
async def big_select_table(io: IO):
    data = [
        {"a": i, "b": 2 * i, "c": 3 * i, "d": [i, i, i], "e": {"i": i}}
        for i in range(100_000)
    ]

    selected = await io.select.table(
        "Table",
        data=data,
    )

    print(selected)

    return {row["a"]: True for row in selected}


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
    [name, num, d, color] = await io.group(
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

    print(name, num, d, color)

    return {
        "Name": name if name is not None else "No name selected",
        "Number": num if num is not None else "No number selected",
        "Date": d if d is not None else "No date selected",
        "Favorite color": color["label"] if color is not None else "Unknown",
    }


@interval.action_with_slug("io.search")
async def io_search(io: IO):
    states = [
        "Alabama",
        "Alaska",
        "Arizona",
        "Arkansas",
        "California",
        "Colorado",
        "Connecticut",
        "Delaware",
        "Florida",
        "Georgia",
        "Hawaii",
        "Idaho",
        "Illinois",
        "Indiana",
        "Iowa",
        "Kansas",
        "Kentucky",
        "Louisiana",
        "Maine",
        "Maryland",
        "Massachusetts",
        "Michigan",
        "Minnesota",
        "Mississippi",
        "Missouri",
        "Montana",
        "Nebraska",
        "Nevada",
        "New Hampshire",
        "New Jersey",
        "New Mexico",
        "New York",
        "North Carolina",
        "North Dakota",
        "Ohio",
        "Oklahoma",
        "Oregon",
        "Pennsylvania",
        "Rhode Island",
        "South Carolina",
        "South Dakota",
        "Tennessee",
        "Texas",
        "Utah",
        "Vermont",
        "Virginia",
        "Washington",
        "West Virginia",
        "Wisconsin",
        "Wyoming",
    ]

    async def on_search(query: str):
        return [state for state in states if query.lower() in str(state).lower()]

    def render_result(state: str) -> RenderableSearchResult:
        return {
            "label": state,
            "image": {
                "url": f"https://geology.com/state-map/maps/{str(state).lower()}-county-map.gif",
            },
        }

    state = await io.search(
        "Search for state",
        on_search=on_search,
        render_result=render_result,
        initial_results=states,
    )

    return {"selected_state": state}


@interval.action
async def validity_tester(io: IO):
    async def validate(
        _name: str, _email: str, age: int | None, include_drink_tickets: bool
    ):
        await asyncio.sleep(0.1)
        if (age is None or age < 21) and include_drink_tickets:
            return "Attendees must be 21 years or older to receive drink tickets."

    await io.group(
        io.input.text("Name"),
        io.input.email("Email").validate(
            lambda s: "Must be an Interval employee"
            if not s.endswith("@interval.com")
            else None
        ),
        io.input.number("Age").optional(),
        io.input.boolean("Include drink tickets?"),
    ).validate(validate)

    await io.group(
        io.input.text("Name"),
        io.input.email("Email").validate(
            lambda s: "Must be an Interval employee"
            if not s.endswith("@interval.com")
            else None
        ),
        io.input.number("Age").optional(),
        io.input.boolean("Include drink tickets?"),
    ).validate(
        lambda _name, _email, age, include_drink_tickets: "Attendees must be 21 years or older to receive drink tickets."
        if (age is None or age < 21) and include_drink_tickets
        else None
    )


@interval.action_with_slug("io.input.file")
async def input_file(io: IO):
    file = await io.input.file(
        "Upload file!", help_text="From python!", allowed_extensions=[".txt", ".json"]
    )

    text = await file.text()

    return {"file_name": file.name, "contents": text}


@interval.action_with_slug("io.confirm_identity")
async def confirm_identity(io: IO):
    name = await io.input.text("Please enter your name")
    can_do = await io.confirm_identity(
        "This is a sensitive action", grace_period_ms=600000
    )

    if can_do:
        return {"confirmed": True}
    else:
        return {"confirmed": False}


interval.listen()
