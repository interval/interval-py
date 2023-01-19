import asyncio, json, signal
from datetime import date, datetime
from typing import Iterable, Optional, cast
from typing_extensions import Literal, NotRequired
from urllib.parse import urlparse

import boto3

from interval_sdk import Interval, IO, io_var, ctx_var, action_ctx_var
from interval_sdk.classes.action import Action
from interval_sdk.classes.layout import Layout
from interval_sdk.classes.logger import Logger
from interval_sdk.classes.page import Page
from interval_sdk.components.grid import GridDataFetcherState
from interval_sdk.components.table import TableDataFetcherState
from interval_sdk.internal_rpc_schema import ActionContext
from interval_sdk.io_schema import (
    FileState,
    FileUrlSet,
    GridItem,
    RichSelectOption,
    RenderableSearchResult,
)

prod = Interval(
    "live_N47qd1BrOMApNPmVd0BiDZQRLkocfdJKzvt8W6JT5ICemrAN",
    endpoint="ws://localhost:3000/websocket",
    log_level="debug",
)

interval = Interval(
    "alex_dev_kcLjzxNFxmGLf0aKtLVhuckt6sziQJtxFOdtM19tBrMUp5mj",
    endpoint="ws://localhost:3000/websocket",
    log_level="debug",
    num_message_producers=5,
)


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


def get_state_image(state: str) -> str:
    return f"https://geology.com/state-map/maps/{str(state).lower().replace(' ', '-')}-county-map.gif"


@interval.action
async def group_types(io: IO):
    resp = await io.group(
        io.display.heading("Typed"),
        io.input.text("text"),
        io.input.number("int"),
        io.input.number("float", decimals=2).optional(),
    )
    print(resp)
    resp = await io.group(
        io.display.heading("Fallback"),
        io.input.text("text"),
        io.input.number("int"),
        io.input.number("float", decimals=2).optional(),
        io.input.text("text").optional(),
        io.input.text("text").optional(),
        io.input.text("text").optional(),
        io.input.text("text").optional(),
        io.input.text("text").optional(),
        io.input.text("text").optional(),
        io.input.text("text").optional(),
    )
    print(resp)


@interval.action()
async def group(io: IO):
    await io.group(
        io.display.markdown("1. First item"),
        io.display.markdown("2. Second item"),
    ).continue_button_options(label="Hey!", theme="danger")


@interval.action(name="Hello, Interval!", description="From a Python decorator!")
async def hello_interval():
    return {"hello": "from python!"}


async def manual_action_handler(io: IO):
    await io.display.markdown("IO works!")


manual_action = Action(name="Manual!", handler=manual_action_handler)

interval.routes.add("manual_action", manual_action)

page = Page(name="New page!")


@page.handle
async def handler(display: IO.Display):
    data = [{"a": i, "b": i * 2, "c": i * 3} for i in range(100)]

    async def title():
        await asyncio.sleep(1)
        return "Hey!"

    async def description():
        await asyncio.sleep(0.5)
        raise Exception("Bad description!")
        return "Description??"

    return Layout(
        title=title,
        menu_items=[
            {"label": "Sub action", "route": "new_page/sub_action"},
        ],
        description=description(),
        children=[
            display.markdown("Hey!"),
            display.table("Tables?", data=data),
        ],
    )


@page.action()
async def sub_action():
    return "Hi!"


interval.routes.add("new_page", page)


@interval.action
async def keyed_group(io: IO):
    res = await io.group(
        name=io.input.text("Name"),
        num=io.input.number("Number?").optional(),
    )

    print(res)

    return {
        "name": res.name,
        "num": res.num,
    }


@interval.action
async def log_test():
    ctx = action_ctx_var.get()
    for i in range(10):
        await ctx.log("hi!", i)


@prod.action()
@interval.action()
async def loading_test():
    ctx = action_ctx_var.get()
    await ctx.loading.start("Fetching users...")

    await asyncio.sleep(1)

    num_users = 100

    await ctx.loading.start(
        title="Exporting users",
        description="We're exporting all users. This may take a while.",
        items_in_queue=num_users,
    )
    for _ in range(num_users):
        await asyncio.sleep(0.1)
        await ctx.loading.complete_one()
    await ctx.loading.start("Finishing up...")

    await asyncio.sleep(1)


@interval.action
async def notify(io: IO, ctx: ActionContext):
    deliveries = []

    more_deliveries = True
    while more_deliveries:
        [_heading, to, method, more_deliveries] = await io.group(
            io.display.heading("Let's send a notification"),
            io.input.text("To"),
            io.select.single(
                "Method",
                options=[
                    "SLACK",
                    "EMAIL",
                ],
            ).optional(),
            io.input.boolean("Send another?"),
        )

        deliveries.append(
            {
                "to": to,
                "method": method,
            }
        )
        await ctx.log("Current delivery array:", deliveries)

    [message, title] = await io.group(
        io.input.text("Message"), io.input.text("Title").optional()
    )

    await ctx.notify(message=message, title=title, delivery=deliveries)

    return "OK, notified!"


@interval.action
async def redirect(io: IO, ctx: ActionContext):
    [url, _, route, params_str] = await io.group(
        io.input.url("URL").optional(),
        io.display.markdown("--- or ---"),
        io.input.text("Route").optional(),
        io.input.text("Params", multiline=True).optional(),
    )

    params: Optional[dict] = None
    if url is not None:
        await ctx.redirect(url=url.geturl())
    elif route is not None:
        if params_str is not None:
            try:
                params = json.loads(params_str)
            except:
                await ctx.log("Invalid params object", params_str)
        await ctx.redirect(route=route, params=params)
    else:
        raise Exception("Must enter either URL or route")

    return {
        "url": url.geturl() if url is not None else None,
        "route": route,
        "params": params_str,
    }


@interval.action
async def throw_error():
    raise Exception("Error!")


@prod.action()
@interval.action()
async def echo_message():
    io = io_var.get()
    [message] = await io.group(io.input.text("Hello!", help_text="From python!"))

    return message


@prod.action()
@interval.action()
async def context():
    ctx = ctx_var.get()
    return {
        "user": f"{ctx.user.first_name} {ctx.user.last_name}",
        "message": ctx.params.get("message", None),
        "environment": ctx.environment,
    }


@interval.action
async def heading(io: IO):
    await io.display.heading(
        "Section heading",
        level=2,
        description="A section heading here",
        menu_items=[
            {
                "label": "Link",
                "url": "https://interval.com",
                "theme": "primary",
            },
            {
                "label": "Danger",
                "route": "disabled_inputs",
                "theme": "danger",
            },
        ],
    )


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
                        "extraData": True,
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
    basic = await io.select.multiple("Just strings", options=["a", "b"])
    print(basic)

    both = await io.select.multiple(
        "Both", options=["string", {"label": "object", "value": "object"}]
    )
    print(both)

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

    ret: dict[str, Optional[bool]] = {}

    for option in options:
        ret[str(option["label"])] = option["value"] in selected_values

    ret["extraData"] = selected[1]["extraData"] if "extraData" in selected[1] else None

    print(ret)

    return ret


@prod.action(slug="add-two-numbers", backgroundable=True)
@interval.action(slug="add-two-numbers", backgroundable=True)
async def add_two_numbers():
    io = io_var.get()
    n1 = await io.input.number("First number")
    n2 = await io.input.number(
        "Second number",
        min=n1,
        decimals=2,
        help_text=f"Must be greater than {n1}",
    )

    print("sum", n1 + n2)

    return {"n1": n1, "n2": n2, "sum": n1 + n2, "from": "🐍"}


@interval.action(slug="io.display.code")
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


@interval.action(slug="io.display.link")
async def io_display_link(io: IO):
    await io.display.link(
        "Code",
        route="io.display.code",
        params={"hello": "world"},
    )

    return "All done!"


@interval.action(slug="io.display.video")
async def io_display_video(io: IO):
    await io.display.video(
        "Video via url",
        url="https://upload.wikimedia.org/wikipedia/commons/a/ad/The_Kid_scenes.ogv",
        size="large",
    )

    return "All done!"


@interval.action(slug="io.display.metadata")
async def io_display_metadata(io: IO):
    layout = await io.select.single(
        "Layout",
        options=cast(
            list[Literal["list", "grid", "card"]],
            ["list", "grid", "card"],
        ),
        default_value="list",
    )

    await io.display.metadata(
        "User info",
        layout=layout,
        data=[
            {"label": "Name", "value": "Alex"},
            {"label": "Email", "value": "alex@interval.com"},
            {"label": "Friends", "value": 24},
        ],
    )

    return "All done!"


@interval.action("io.input.url")
async def io_input_url(io: IO):
    url, opt_url = await io.group(
        io.input.url("One URL please"),
        io.input.url("A URL, if you want").optional(),
    )

    print("url", url)
    print("opt_url", opt_url)

    return {"url": str(url), "opt_url": str(opt_url)}


@interval.action("io.display.object")
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


tables = Page("Tables")

interval.routes.add("tables", tables)


@tables.action
async def asynchronous():
    io = io_var.get()

    async def get_data(state: TableDataFetcherState):
        return [
            {"a": i + state.offset, "b": i * 10} for i in range(state.page_size)
        ], 100

    await io.display.table(
        "Async",
        get_data=get_data,
        row_menu_items=lambda row: [
            {
                "label": "Link",
                "url": "https://interval.com",
            },
            {
                "label": "Danger action",
                "theme": "danger",
                "route": "context",
                "params": {"message": f"Hi from {row['a']}!"},
            },
        ],
        is_sortable=False,
        is_filterable=False,
    )


@tables.action
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
                    "url": f"https://example.com/{row['b']}",
                    "image": {
                        "url": f"https://avatars.dicebear.com/api/pixel-art/{row['b']}.svg?scale=96&translateY=10",
                        "size": "small",
                    },
                },
            },
            "c",
            {"label": "D", "accessorKey": "d"},
        ],
        row_menu_items=lambda row: [
            {
                "label": "Link",
                "url": "https://interval.com",
            },
            {
                "label": "Danger action",
                "theme": "danger",
                "route": "context",
                "params": {"message": f"Hi from {row['a']}!"},
            },
        ],
    )

    print(selected)


@tables.action
async def big_table(io: IO):
    data = [
        {"a": i, "b": 2 * i, "c": 3 * i, "d": [i, i, i], "e": {"i": i}}
        for i in range(10_000)
    ]

    await io.display.table(
        "Table",
        data=data,
        default_page_size=50,
    )


@tables.action
async def big_select_table(io: IO):
    data = [
        {"a": i, "b": 2 * i, "c": 3 * i, "d": [i, i, i], "e": {"i": i}}
        for i in range(10_000)
    ]

    selected = await io.select.table(
        "Table",
        data=data,
        default_page_size=50,
        is_sortable=False,
    )

    print(selected)

    return {row["a"]: True for row in selected}


grids = Page("Grids")


@grids.action
async def data():
    io = io_var.get()
    await io.display.grid(
        "Basic",
        help_text="With static data",
        data=list(range(100)),
        render_item=lambda x: {
            "title": f"Item {x}",
        },
        default_page_size=10,
        is_filterable=False,
    )


@grids.action
async def get_data():
    io = io_var.get()

    def render_item(state: str) -> GridItem:
        return {
            "title": state,
            "description": f"The great state of {state}",
            "image": {
                "url": get_state_image(state),
                "alt": state,
                "aspectRatio": 1,
                "fit": "contain",
            },
            "menu": [
                {
                    "label": "Learn more",
                    "url": f"https://wikipedia.org/wiki/{state}",
                }
            ],
            "url": f"https://www.{state.lower()}.gov",
        }

    async def get_data(state: GridDataFetcherState):
        if state.query_term is None or state.query_term == "":
            data = states
        else:
            data = [s for s in states if state.query_term.lower() in s.lower()]

        return data[state.offset : state.offset + state.page_size], len(data)

    await io.display.grid(
        "Async",
        help_text="With get_data",
        get_data=get_data,
        render_item=render_item,
        ideal_column_width=200,
    )


interval.routes.add("grids", grids)


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


search = Page("Search")


@search.action("io.search")
async def io_search(io: IO):
    async def on_search(query: str):
        return [state for state in states if query.lower() in str(state).lower()]

    def render_result(state: str) -> RenderableSearchResult:
        return {
            "label": state,
            "image": {
                "url": get_state_image(state),
            },
        }

    state = await io.search(
        "Search for state",
        on_search=on_search,
        render_result=render_result,
        initial_results=states,
    ).optional()

    return {"selected_state": state}


@search.action
async def multi_search(io: IO):
    async def on_search(query: str):
        return [state for state in states if query.lower() in str(state).lower()]

    def render_result(state: str) -> RenderableSearchResult:
        return {
            "label": state,
            "image": {
                "url": get_state_image(state),
            },
        }

    def check_for_illinois(states: Optional[Iterable[str]]) -> Optional[str]:
        if states is None:
            return None

        return "Illinois is not allowed." if "Illinois" in states else None

    selected = (
        await io.search(
            "Search for state (no Illinois)",
            on_search=on_search,
            render_result=render_result,
            initial_results=states,
        )
        .multiple(default_value=["Wisconsin"])
        .optional()
        .validate(check_for_illinois)
    )

    return {"selected_state": ", ".join(selected) if selected is not None else None}


interval.routes.add("search", search)


@interval.action
async def validity_tester(io: IO):
    async def validate(
        name: str, email: str, age: Optional[int], include_drink_tickets: bool
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

    await io.group(
        name=io.input.text("Name"),
        email=io.input.email("Email").validate(
            lambda s: "Must be an Interval employee"
            if not s.endswith("@interval.com")
            else None
        ),
        age=io.input.number("Age").optional(),
        include_drink_tickets=io.input.boolean("Include drink tickets?"),
    ).validate(validate)


files = Page("Files")


@files.action("io.input.file")
async def input_file(io: IO):
    file = await io.input.file(
        "Upload file!", help_text="From python!", allowed_extensions=[".txt", ".json"]
    )

    text = file.text()

    return {
        "file_name": file.name,
        "extension": file.extension,
        "contents": text,
    }


@files.action
async def upload_custom_endpoint(io: IO):
    async def generate_presigned_urls(file: FileState) -> FileUrlSet:
        url_safe_name = file.name.replace(" ", "-")
        path = f"test-runner/{int(datetime.now().timestamp())}-{url_safe_name}"
        s3_client = boto3.client("s3")
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": "interval-io-uploads-dev",
                "Key": path,
            },
            ExpiresIn=3600,  # 1 hour
            HttpMethod="PUT",
        )
        url = urlparse(upload_url)
        url = url._replace(params="", query="", fragment="")
        download_url = url.geturl()

        print(
            upload_url,
            download_url,
        )

        return {
            "uploadUrl": upload_url,
            "downloadUrl": download_url,
        }

    file = await io.input.file(
        "Upload a file",
        generate_presigned_urls=generate_presigned_urls,
    )

    return {
        "size": file.size,
        "type": file.type,
        "name": file.name,
        "extension": file.extension,
        "url": file.url,
    }


@files.action
async def multiple(io: IO):
    files = (
        await io.input.file(
            "Upload images",
            help_text="From python!",
            allowed_extensions=[".png", ".jpg", ".jpeg"],
        )
        .multiple()
        .optional()
    )

    if files is None:
        return

    await io.group(*(io.display.image(file.name, url=file.url) for file in files))

    return {file.name: file.size for file in files}


interval.routes.add("files", files)


@interval.action("io.confirm_identity")
async def confirm_identity(io: IO):
    _name = await io.input.text("Please enter your name")
    can_do = await io.confirm_identity("This is a sensitive action", grace_period=600)

    if can_do:
        return {"confirmed": True}
    else:
        return {"confirmed": False}


@interval.action
async def disabled_inputs(io: IO):
    await io.group(
        io.display.heading("Here are a bunch of disabled inputs"),
        io.input.text("Name", disabled=True, placeholder="I am a placeholder"),
        io.input.email("Email", disabled=True, placeholder="foo@bar.com"),
        io.input.number("Age", disabled=True, placeholder="21"),
        io.input.boolean("True or false?", disabled=True),
        io.input.date("Date", disabled=True),
        io.input.time("Time", disabled=True),
        io.input.datetime("Date and time", disabled=True),
        io.input.file("File", disabled=True),
        io.select.single(
            "Single select",
            disabled=True,
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
        ),
        io.select.multiple(
            "Multi select",
            disabled=True,
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
        ),
        io.select.table("Table select", data=[{"foo": "bar"}], disabled=True),
    )
    return "All done!"


@interval.action
async def redirect_url(io: IO, ctx: ActionContext):
    url = (await io.input.url("Enter a URL")).geturl()
    await ctx.redirect(url=url)
    return {"url": url}


@interval.action(unlisted=True)
async def unlisted_action():
    return "Hello, world!"


unlisted_page = Page("Unlisted page", unlisted=True)


@unlisted_page.action
async def unlisted_listed():
    return "Hello, world!"


interval.routes.add("unlisted_page", unlisted_page)

dynamic_group = Page(name="Dynamic")


@dynamic_group.action
async def placeholder():
    # Just here to prevent this group from disappearing when self_destructing removes itself
    pass


@dynamic_group.action
async def self_destructing():
    dynamic_group.remove("self_destructing")
    return "Goodbye!"


def on_listened(task: asyncio.Task):
    try:
        task.result()

        @interval.action
        async def after_listen():
            return "Hello, from the future!"

        interval.routes.add("dynamic_group", dynamic_group)
    except:
        pass


logger = Logger(log_level="debug")

loop = asyncio.get_event_loop()
prod_task = loop.create_task(prod.listen_async())
prod_task.add_done_callback(logger.handle_task_exceptions)

dev_task = loop.create_task(interval.listen_async())
dev_task.add_done_callback(logger.handle_task_exceptions)
dev_task.add_done_callback(on_listened)

for sig in {signal.SIGINT, signal.SIGTERM}:
    loop.add_signal_handler(sig, loop.stop)

loop.run_forever()
