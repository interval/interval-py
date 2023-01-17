import asyncio
import json, re
from datetime import date, time, datetime
from pathlib import Path
from typing import Union, cast

from typing_extensions import NotRequired, TypedDict

from playwright.async_api import Page as BrowserPage, expect
import pytest

from interval_sdk import (
    Interval,
    IO,
    ActionContext,
    io_var,
    action_ctx_var,
    ctx_var,
    Page,
    Layout,
)
from interval_sdk.io_schema import LabelValue, RenderableSearchResult, RichSelectOption

from . import Transaction
from .data.mock_db import MockDb
from .utils.date import input_date, input_time


async def test_context(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action
    async def context(_, ctx_arg: ActionContext):
        ctx = ctx_var.get()
        assert ctx_arg == ctx

        return {
            "user": f"{ctx.user.first_name} {ctx.user.last_name}",
            "message": ctx.params.get("message", None),
            "environment": ctx.environment,
        }

    await transactions.console()
    await transactions.run("context")
    await page.goto(page.url + "?message=Hello")
    await transactions.expect_success(
        user="Test Runner", message="Hello", environment="development"
    )


async def test_display_heading(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.display.heading")
    async def display_heading():
        io = io_var.get()

        await io.display.heading("io.display.heading result")

        await io.display.heading(
            "Section heading",
            level=3,
            description="Sub-heading",
            menu_items=[
                {
                    "label": "External link item",
                    "url": "https://interval.com",
                },
                {
                    "label": "Action link item",
                    "route": "context",
                    "params": {"param": "true"},
                },
            ],
        )

    await transactions.console()
    await transactions.run("io.display.heading")
    await expect(page.locator("text=io.display.heading result")).to_be_visible()
    await transactions.press_continue()

    await expect(page.locator("text=Section heading")).to_be_visible()
    await expect(page.locator("text=Sub-heading")).to_be_visible()
    await expect(page.locator("text=Sub-heading")).to_be_visible()
    await expect(page.locator('a:has-text("External link item")')).to_have_attribute(
        "href",
        "https://interval.com",
    )
    await expect(page.locator('a:has-text("Action link item")')).to_have_attribute(
        "href",
        "/dashboard/test-runner/develop/actions/context?param=true",
    )

    await transactions.press_continue()

    await transactions.expect_success()


async def test_group(interval: Interval, page: BrowserPage, transactions: Transaction):
    @interval.action("io.group")
    async def group(io: IO):
        await io.group(
            io.display.markdown("1. First item"),
            io.display.markdown("2. Second item"),
        )

        await io.group(io.display.markdown("1. First item")).continue_button_options(
            label="Custom label",
            theme="danger",
        )

        resp = await io.group(
            text=io.input.text("Text"), num=io.input.number("Number").optional()
        )

        return {**resp}

    await transactions.console()
    await transactions.run("io.group")
    await expect(page.locator("text=First item")).to_be_visible()
    await expect(page.locator("text=Second item")).to_be_visible()
    await transactions.press_continue()

    button = page.locator('button:has-text("Custom label")')
    await expect(button).to_be_visible()
    await expect(button).to_have_class(re.compile("bg-red-500"))
    await transactions.press_continue("Custom label")

    await page.click("text=Text")
    await page.keyboard.type("Hello")
    await page.click("text=Number")
    await page.keyboard.type("1337")
    await transactions.press_continue()

    await transactions.expect_success(text="Hello", num="1,337")


async def test_display_image(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.display.image")
    async def display_image(io: IO):
        await io.display.image(
            "Image via URL",
            url="https://media.giphy.com/media/26ybw6AltpBRmyS76/giphy.gif",
            alt="Man makes like he's going to jump on a skateboard but doesn't",
            size="medium",
        )

        path = Path(__file__).parent / "data/fail.gif"
        with open(path, "rb") as image:
            await io.display.image(
                "Image via bytes",
                bytes=image.read(),
                alt="Wile E. Coyote pulls a rope to launch a boulder from a catapult but it topples backwards and crushes him",
            )

    await transactions.console()
    await transactions.run("io.display.image")

    await expect(page.locator("text=Image via URL")).to_be_visible()
    img = page.locator("img[data-pw-display-image]")
    await expect(img).to_be_visible()
    await expect(img).to_have_attribute(
        "src", "https://media.giphy.com/media/26ybw6AltpBRmyS76/giphy.gif"
    )
    await expect(img).to_have_class(re.compile("w-img-medium"))
    assert await img.get_attribute("alt") is not None
    await transactions.press_continue()

    await expect(page.locator("text=Image via bytes")).to_be_visible()
    img = page.locator("img[data-pw-display-image]")
    await expect(img).to_be_visible()
    src = await img.get_attribute("src")
    assert src is not None and src.startswith("data:")
    assert await img.get_attribute("alt") is not None
    await transactions.press_continue()

    await transactions.expect_success()


async def test_display_object(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.display.object")
    async def display_object(io: IO):
        await io.display.object(
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
            },
        )

    await transactions.console()
    await transactions.run("io.display.object")
    await expect(page.locator('dt:has-text("isTrue")')).to_be_visible()
    await expect(page.locator('dd:has-text("true")')).to_be_visible()
    await expect(page.locator('dt:has-text("none_value")')).to_be_visible()
    await expect(page.locator('dd:has-text("null")')).to_be_visible()
    await expect(page.locator('dt:has-text("name")')).to_be_visible()
    await expect(page.locator('dd:has-text("Interval")')).to_be_visible()
    await expect(page.locator('summary:has-text("longList")')).to_be_visible()
    await expect(page.locator('dd:has-text("Item 99")')).to_be_hidden()
    await page.locator('summary:has-text("longList")').click()
    await expect(page.locator('dd:has-text("Item 99")')).to_be_visible()
    await transactions.press_continue()
    await transactions.expect_success()


async def test_display_metadata(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.display.metadata")
    async def display_metadata(io: IO):
        data = [
            {
                "label": "Is true",
                "value": True,
            },
            {
                "label": "Is false",
                "value": False,
            },
            {
                "label": "Is null",
                "value": None,
            },
            {
                "label": "Is empty string",
                "value": "",
            },
            {
                "label": "Is long string",
                "value": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed sit amet quam in lorem",
            },
            {
                "label": "Is number 15",
                "value": 15,
            },
            {
                "label": "Is string",
                "value": "Hello",
            },
            {
                "label": "Action link",
                "value": "Click me",
                "action": "helloCurrentUser",
                "params": {"message": "Hello from metadata!"},
            },
            {
                "label": "Image",
                "value": "Optional caption",
                "image": {
                    "url": "https://picsum.photos/200/300",
                    "width": "small",
                    "height": "small",
                },
            },
        ]

        await io.display.metadata("Metadata list", data=data)
        await io.display.metadata("Metadata grid", layout="grid", data=data)
        await io.display.metadata("Metadata card", layout="card", data=data)

    await transactions.console()
    await transactions.run("io.display.metadata")
    for layout in ["list", "grid", "card"]:
        await expect(page.locator(f'h4:has-text("Metadata {layout}")')).to_be_visible()

        await expect(page.locator('dt:has-text("Is true")')).to_be_visible()
        await expect(page.locator('dd:has-text("true")')).to_be_visible()
        await expect(page.locator('dt:has-text("Is false")')).to_be_visible()
        await expect(page.locator('dd:has-text("false")')).to_be_visible()
        await expect(page.locator('dt:has-text("Is null")')).to_be_visible()
        await expect(page.locator('dt:has-text("Is empty")')).to_be_visible()
        await expect(page.locator('dt:has-text("Is long string")')).to_be_visible()
        await expect(
            page.locator(
                'dd:has-text("Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed sit amet quam in lorem")'
            )
        ).to_be_visible()
        await expect(page.locator('dt:has-text("Is number 15")')).to_be_visible()
        await expect(page.locator('dd:has-text("15")')).to_be_visible()
        await expect(page.locator('dt:has-text("Is string")')).to_be_visible()
        await expect(page.locator('dd:has-text("Hello")')).to_be_visible()
        await expect(page.locator('dt:has-text("Action link")')).to_be_visible()
        await expect(page.locator('dd a:has-text("Click me")')).to_be_visible()
        await transactions.press_continue()

    await transactions.expect_success()


async def test_display_table(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.display.table")
    async def display_table(io: IO):
        await io.display.table(
            "io.display.table result",
            data=[
                {
                    "string": "string",
                    "number": 15,
                    "boolean": True,
                    "none": None,
                }
            ],
        )

    await transactions.console()
    await transactions.run("io.display.table")
    await expect(page.locator("text=io.display.table result")).to_be_visible()
    await expect(
        page.locator('[role="columnheader"]:has-text("string")')
    ).to_be_visible()
    await expect(page.locator('[role="cell"]:has-text("string")')).to_be_visible()
    await expect(
        page.locator('[role="columnheader"]:has-text("number")')
    ).to_be_visible()
    await expect(page.locator('[role="cell"]:has-text("15")')).to_be_visible()
    await expect(
        page.locator('[role="columnheader"]:has-text("boolean")')
    ).to_be_visible()
    await expect(page.locator('[role="cell"]:has-text("true")')).to_be_visible()
    await expect(page.locator('[role="columnheader"]:has-text("none")')).to_be_visible()
    await expect(page.locator('[role="cell"]:has-text("-")')).to_be_visible()
    await transactions.press_continue()
    await transactions.expect_success()


async def test_input_text(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.input.text")
    async def io_input_text(io: IO):
        name = await io.input.text("First name", min_length=5, max_length=20)
        return {"name": name}

    await transactions.console()
    await transactions.run("io.input.text")

    await transactions.press_continue()
    await transactions.expect_validation_error()

    await page.click("text=First name")
    input = page.locator('input[type="text"]')
    message = "Please enter a value with between 5 and 20 characters."

    await input.fill("Int")
    await transactions.press_continue()
    await transactions.expect_validation_error(message)

    await input.fill("Interval Interval Interval Interval")
    await transactions.press_continue()
    await transactions.expect_validation_error(message)

    await input.fill("Interval")
    await transactions.press_continue()
    await transactions.expect_success(name="Interval")


async def test_input_email(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.input.email")
    async def io_input_email(io: IO):
        email = await io.input.email("Email address")
        return {"email": email}

    await transactions.console()
    await transactions.run("io.input.email")

    await page.click("text=Email address")
    await page.keyboard.type("notanemail")
    await transactions.press_continue()
    # will be prevented by browser email validator

    await page.click("text=Email address")
    await page.keyboard.type("hello@interval.com")
    await transactions.press_continue()
    await transactions.expect_success(email="hello@interval.com")


class TestInputNumber:
    async def test_input_number(
        self, interval: Interval, page: BrowserPage, transactions: Transaction
    ):
        @interval.action("io.input.number")
        async def input_number(io: IO):
            num = await io.input.number("Enter a number")
            num2 = await io.input.number(
                f"Enter a second number that's greater than {num}", min=num + 1
            )

            return {"sum": num + num2}

        await transactions.console()
        await transactions.run("io.input.number")

        await page.click("text=Enter a number")
        await page.fill('input[inputmode="numeric"]', "12")
        await transactions.press_continue()

        await page.click("text=Enter a second number")
        await page.fill('input[inputmode="numeric"]', "7")
        await transactions.press_continue()
        await transactions.expect_validation_error(
            "Please enter a number greater than or equal to 13."
        )
        await page.fill('input[inputmode="numeric"]', "13")

        await transactions.press_continue()
        await transactions.expect_success(sum="25")

    async def test_currency(
        self, interval: Interval, page: BrowserPage, transactions: Transaction
    ):
        @interval.action
        async def currency(io: IO):
            return await io.group(
                usd=io.input.number("United States Dollar", min=10, currency="USD"),
                eur=io.input.number("Euro", currency="EUR"),
                jpy=io.input.number("Japanese yen", currency="JPY", decimals=3),
            )

        await transactions.console()
        await transactions.run("currency")

        await page.locator("text=United States Dollar").click()
        await page.keyboard.type("9.99")
        await page.locator("text=Euro").click()
        await page.keyboard.type("10.001")
        await page.locator("text=Japanese yen").click()
        await page.keyboard.type("12.345")
        await transactions.press_continue()
        await transactions.expect_validation_error(
            "Please enter a number greater than or equal to 10."
        )
        await transactions.expect_validation_error(
            "Please enter a number with up to 2 decimal places."
        )
        await page.locator("input").nth(0).fill("10")
        await page.locator("input").nth(1).fill("10.01")

        await transactions.press_continue()
        await transactions.expect_success(
            usd="10",
            eur="10.01",
            jpy="12.345",
        )


async def test_input_rich_text(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.input.richText")
    async def rich_text(io: IO):
        body = await io.input.rich_text("Email body")
        await io.display.markdown(
            f"""
            ## You entered:

            ```
            {body}
            ```
            """
        )

    await transactions.console()
    await transactions.run("io.input.richText")
    await expect(page.locator("text=Email body")).to_be_visible()

    input = page.locator(".ProseMirror")

    await page.select_option('select[aria-label="Heading level"]', "1")
    await input.type("Heading 1")
    await input.press("Enter")
    await page.click('button[aria-label="Toggle italic"]')
    await input.type("Emphasis")
    await input.press("Enter")
    await page.click('button[aria-label="Toggle italic"]')
    await page.click('button[aria-label="Toggle underline"]')
    await input.type("Underline")
    await page.click('button[aria-label="Toggle underline"]')

    await transactions.press_continue()
    await expect(page.locator('h2:has-text("You entered:")')).to_be_visible()
    await expect(page.locator("pre code")).to_contain_text(
        "<h1>Heading 1</h1><p><em>Emphasis</em></p><p><u>Underline</u></p>\n"
    )
    await transactions.press_continue()
    await transactions.expect_success()


async def test_confirm(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action
    async def confirm(io: IO):
        first = await io.confirm("Are you sure?", help_text="Really sure?")
        second = await io.confirm("Still?")

        return {
            "first": first,
            "second": second,
        }

    await transactions.console()
    await transactions.run("confirm")

    await expect(page.locator("text=Are you sure?")).to_be_visible()
    await expect(page.locator("text=Really sure?")).to_be_visible()
    await page.locator('button:has-text("Confirm")').click()

    await expect(page.locator("text=Still?")).to_be_visible()
    await page.locator('button:has-text("Cancel")').click()

    await transactions.expect_success(first="true", second="false")


async def test_confirm_identity(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action
    async def confirm_identity(io: IO):
        first = await io.confirm_identity("First", grace_period=0)
        second = await io.confirm_identity("Second")
        third = await io.confirm_identity("Third", grace_period=0)

        return {
            "first": first,
            "second": second,
            "third": third,
        }

    await transactions.console()
    await transactions.run("confirm_identity")

    await expect(
        page.locator("text=Please confirm your identity to continue")
    ).to_be_visible()
    await expect(page.locator("text=First")).to_be_visible()
    await page.fill('input[type="password"]', transactions.config.login.password)
    await page.locator('button:has-text("Verify")').click()
    await expect(page.locator("text=Second")).to_be_hidden()
    await expect(page.locator("text=Third")).to_be_visible()
    await page.locator('button:has-text("Cancel")').click()

    await transactions.expect_success(
        first="true",
        second="true",
        third="false",
    )


async def test_input_url(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.input.url")
    async def io_input_url(io: IO):
        url = await io.input.url("Enter a URL")
        secure_url = await io.input.url(
            "Enter a secure URL", allowed_protocols=["https"]
        )
        return {
            "url": url.geturl(),
            "secure_url": secure_url.geturl(),
        }

    await transactions.console()
    await transactions.run("io.input.url")

    await transactions.press_continue()
    await transactions.expect_validation_error()

    await page.click("text=Enter a URL")
    input = page.locator('input[type="text"]')
    await input.fill("not a url")
    await transactions.press_continue()
    validation_error_message = "Please enter a valid URL."
    await transactions.expect_validation_error(validation_error_message)

    await input.fill("https://interval.com/?isTest=true&foo=bar")
    await transactions.press_continue()

    secureInput = page.locator('input[type="text"]')
    await secureInput.fill("http://interval.com")
    await transactions.press_continue()
    await transactions.expect_validation_error("The URL must begin with https.")

    await secureInput.fill("https://interval.com")
    await transactions.press_continue()
    await transactions.expect_success(
        url="https://interval.com/?isTest=true&foo=bar",
        secure_url="https://interval.com",
    )


async def test_select_single(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.select.single")
    async def select_single(io: IO):
        basic = await io.select.single(
            "Choose basic", options=[1, True, date(2022, 7, 20)]
        )

        selected = await io.select.single(
            "Choose custom",
            options=[
                {"label": "Admin", "value": "a"},
                # TODO: See if there's a better way to do this
                cast(
                    RichSelectOption,
                    {"label": "Editor", "value": 2, "extraData": True},
                ),
                {"label": "Viewer", "value": "c"},
            ],
        )

        return {
            "basic": basic,
            "basic_type": type(basic).__name__,
            **selected,
        }

    await transactions.console()
    await transactions.run("io.select.single")

    await transactions.press_continue()
    await transactions.expect_validation_error()

    await page.click(".iv-select-container")
    await page.locator('.iv-select__menu div div:has-text("2022")').click()
    await transactions.press_continue()

    label = page.locator('label:has-text("Choose custom")')
    inputId = await label.get_attribute("for")
    input = page.locator(f"#{inputId}")
    await input.click()
    await page.locator('.iv-select__menu div div:has-text("Admin")').click()
    await expect(page.locator(".iv-select__single-value")).to_contain_text("Admin")

    await input.fill("ed")
    await input.press("Enter")
    await transactions.press_continue()

    await transactions.expect_success(
        basic=date(2022, 7, 20).isoformat(),
        basic_type="date",
        label="Editor",
        value="2",
        extraData="true",
    )


async def test_select_multiple(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.select.multiple")
    async def select_multiple(io: IO):
        class Option(LabelValue):
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

        basic_selected = await io.select.multiple(
            "Select zero or more", options=[o["value"] for o in options]
        )

        selected = await io.select.multiple(
            "Optionally modify the selection, selecting between 1 and 2",
            options=options,
            default_value=[o for o in options if o["value"] in basic_selected],
            min_selections=1,
            max_selections=2,
        )

        selected_values = [o["value"] for o in selected]
        ret: dict[str, bool] = {}

        for option in options:
            ret[str(option["label"])] = option["value"] in selected_values

        return {
            **ret,
            "extraData": selected[0].get("extraData", None),
        }

    await transactions.console()
    await transactions.run("io.select.multiple")

    date_val = date(2022, 6, 20).isoformat()

    await expect(page.locator("text=Select zero or more")).to_be_visible()
    await page.click(f'input[type="checkbox"][value="{date_val}"]')
    await page.click('input[type="checkbox"][value="true"]')
    await page.click('input[type="checkbox"][value="3"]')
    await transactions.press_continue()

    await expect(page.locator("text=Optionally modify the selection")).to_be_visible()
    await expect(
        page.locator(f'input[type="checkbox"][value="{date_val}"]')
    ).to_be_checked()
    await expect(page.locator('input[type="checkbox"][value="true"]')).to_be_checked()
    await expect(page.locator('input[type="checkbox"][value="3"]')).to_be_checked()

    await transactions.press_continue()
    await transactions.expect_validation_error("Please make no more than 2 selections.")
    await page.click(f'input[type="checkbox"][value="{date_val}"]')
    await page.click('input[type="checkbox"][value="true"]')
    await page.click('input[type="checkbox"][value="3"]')
    await transactions.press_continue()
    await transactions.expect_validation_error("Please make at least 1 selection.")

    await page.click(f'input[type="checkbox"][value="{date_val}"]')
    await page.click('input[type="checkbox"][value="3"]')
    await transactions.press_continue()

    await transactions.expect_success(
        **{
            date_val: "true",
            "True": "false",
            "3": "true",
            "extraData": "true",
        }
    )


async def test_select_invalid_defaults(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action
    async def select_invalid_defaults(io: IO):
        await io.group(
            io.select.single(
                "Choose one",
                options=[],
                default_value={"label": "Invalid", "value": "invalid"},
            ),
            io.select.multiple(
                "Choose some",
                options=[],
                default_value=[
                    {"label": "Invalid", "value": "invalid"},
                    {"label": "Also invalid", "value": "also_invalid"},
                ],
            ),
        )

    await transactions.console()
    await transactions.run("select_invalid_defaults")
    await transactions.press_continue()
    await transactions.expect_validation_error()


async def test_select_table(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action("io.select.table")
    async def select_table(io: IO):
        class Row(TypedDict):
            firstName: str
            lastName: str
            favoriteColor: NotRequired[str]

        data: list[Row] = [
            {"firstName": "Alex", "lastName": "Arena"},
            {"firstName": "Dan", "lastName": "Philibin"},
            {"firstName": "Ryan", "lastName": "Coppolo"},
            {
                "firstName": "Jacob",
                "lastName": "Mischka",
                "favoriteColor": "Orange",
            },
        ]
        selected = await io.select.table(
            "Select some rows",
            data=data,
            min_selections=1,
            max_selections=2,
        )

        await io.display.markdown(
            f"""
            ## You selected:

            ```
            {json.dumps(selected)}
            ```
            """
        )

        selected = await io.select.table(
            "Select some more",
            data=data,
            columns=[
                {
                    "label": "First name",
                    "renderCell": lambda row: row["firstName"],
                },
                {
                    "label": "Last name",
                    "renderCell": lambda row: row["lastName"],
                },
            ],
            min_selections=1,
            max_selections=1,
        )

        return {**selected[0]}

    await transactions.console()
    await transactions.run("io.select.table")

    await expect(page.locator("text=Select some rows")).to_be_visible()
    await transactions.press_continue()
    await transactions.expect_validation_error("Please make at least 1 selection.")
    await page.locator('[role="cell"]:has-text("Orange")').click()
    await page.locator('[role="cell"]:has-text("Dan")').click()
    await page.locator('[role="cell"]:has-text("Ryan")').click()
    await transactions.press_continue()
    await transactions.expect_validation_error("Please make no more than 2 selections.")
    await page.locator('[role="cell"]:has-text("Dan")').click()
    await transactions.press_continue()
    await expect(page.locator("pre code")).to_have_text(
        re.compile(
            r'[{"firstName":"Jacob", "lastName":"Mischka", "favoriteColor":"Orange"}]\s*'
        )
    )
    await transactions.press_continue()

    await page.locator('[role="cell"]:has-text("Alex")').click()
    await page.locator('[role="cell"]:has-text("Dan")').click()
    await transactions.press_continue()
    await transactions.expect_success(firstName="Dan", lastName="Philibin")


async def test_input_date(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action
    async def input_date(io: IO):
        d = await io.input.date(
            "Enter date", min=date(2000, 1, 1), max=date(2022, 12, 30)
        )
        return {
            "year": d.year,
            "month": d.month,
            "day": d.day,
            "py_date": d,
        }

    await transactions.console()
    await transactions.run("input_date")

    await transactions.press_continue()
    await transactions.expect_validation_error()

    input = page.locator('.iv-datepicker input[type="text"]')
    await input.fill("12/34/5678")
    await page.wait_for_timeout(
        200
    )  # wait for 100ms delay we apply before showing the popover
    await input.press("Tab")
    await transactions.press_continue()
    await transactions.expect_validation_error("Please enter a valid date.")

    await input.fill("6/23/1997")
    await page.wait_for_timeout(200)
    await input.press("Tab")
    await transactions.press_continue()
    validationErrorMessage = (
        "Please enter a date between January 1, 2000 and December 30, 2022."
    )
    await transactions.expect_validation_error(validationErrorMessage)

    await input.fill("1/2/2023")
    await page.wait_for_timeout(200)
    await input.press("Tab")
    await transactions.press_continue()
    await transactions.expect_validation_error(validationErrorMessage)

    await input.click()
    await page.wait_for_timeout(200)
    await input.fill("02/22/2022")
    await page.locator('.flatpickr-day:has-text("25")').click()
    await expect(input).to_have_value("02/25/2022")

    await transactions.press_continue()
    await transactions.expect_success(
        year="2,022", month="2", day="25", py_date=date(2022, 2, 25).isoformat()
    )


async def test_input_time(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action
    async def input_time(io: IO):
        t = await io.input.time("Enter time", min=time(8, 30), max=time(20))
        return {
            "hour": t.hour,
            "minute": t.minute,
            "py_time": t,
        }

    await transactions.console()
    await transactions.run("input_time")

    await transactions.press_continue()
    await transactions.expect_validation_error()

    await expect(page.locator(".iv-datepicker")).to_be_visible()
    selects = page.locator(".iv-datepicker select")

    [h, m, ampm] = [selects.nth(0), selects.nth(1), selects.nth(2)]

    await h.select_option(value="8")
    await h.press("Tab")

    await expect(m).to_be_focused()
    await m.type("36")
    await m.press("Tab")

    await expect(ampm).to_be_focused()
    await ampm.select_option("pm")

    await transactions.press_continue()
    validation_error_message = "Please enter a time between 8:30 AM and 8:00 PM."

    await transactions.expect_validation_error(validation_error_message)

    await h.select_option(value="2")
    await ampm.select_option("am")
    await transactions.press_continue()
    await transactions.expect_validation_error(validation_error_message)

    await ampm.select_option("pm")
    await transactions.press_continue()
    await transactions.expect_success(
        hour="14",
        minute="36",
        py_time=time(14, 36).isoformat(),
    )


class TestInputDatetime:
    async def test_input_datetime_basic(
        self, interval: Interval, page: BrowserPage, transactions: Transaction
    ):
        @interval.action
        async def input_datetime(io: IO):
            dt = await io.input.datetime("Enter datetime")
            return {
                "year": dt.year,
                "month": dt.month,
                "day": dt.day,
                "hour": dt.hour,
                "minute": dt.minute,
                "py_datetime": dt,
            }

        await transactions.console()
        await transactions.run("input_datetime")

        await input_date(page)
        await input_time(page)
        await transactions.press_continue()
        await transactions.expect_success(
            year="2,022",
            month="2",
            day="25",
            hour="14",
            minute="36",
            py_datetime=datetime(2022, 2, 25, 14, 36).isoformat(),
        )

    async def test_input_datetime_default(
        self, interval: Interval, page: BrowserPage, transactions: Transaction
    ):
        @interval.action
        async def input_datetime_default(io: IO):
            dt = await io.input.datetime(
                "Enter datetime", default_value=datetime(2020, 6, 23, 13, 25)
            )
            return {
                "year": dt.year,
                "month": dt.month,
                "day": dt.day,
                "hour": dt.hour,
                "minute": dt.minute,
                "py_datetime": dt,
            }

        await transactions.console()
        await transactions.run("input_datetime_default")

        await transactions.press_continue()
        await transactions.expect_success(
            year="2,020",
            month="6",
            day="23",
            hour="13",
            minute="25",
            py_datetime=datetime(2020, 6, 23, 13, 25).isoformat(),
        )

    async def test_input_datetime_min_max(
        self, interval: Interval, page: BrowserPage, transactions: Transaction
    ):
        @interval.action
        async def input_datetime_min_max(io: IO):
            dt = await io.input.datetime(
                "Enter datetime",
                min=datetime(2000, 1, 1, 7, 30),
                max=datetime(2022, 12, 30, 13, 0),
            )
            return {
                "year": dt.year,
                "month": dt.month,
                "day": dt.day,
                "hour": dt.hour,
                "minute": dt.minute,
                "py_datetime": dt,
            }

        await transactions.console()
        await transactions.run("input_datetime_min_max")

        await expect(page.locator(".iv-datepicker")).to_be_visible()
        dateInput = page.locator('.iv-datepicker input[type="text"]')
        await dateInput.fill("1/1/2000")

        selects = page.locator(".iv-datepicker select")
        [h, m, ampm] = [selects.nth(0), selects.nth(1), selects.nth(2)]
        await h.select_option(value="6")
        await m.type("0")
        await ampm.select_option("am")

        validation_error_message = "Please enter a date between Jan 1, 2000, 7:30 AM and Dec 30, 2022, 1:00 PM."

        await transactions.press_continue()
        await transactions.expect_validation_error(validation_error_message)

        await dateInput.fill("12/30/2022")
        await h.select_option(value="8")
        await m.type("45")
        await ampm.select_option("pm")

        await transactions.press_continue()
        await transactions.expect_validation_error(validation_error_message)

        await ampm.select_option("am")

        await transactions.press_continue()
        await transactions.expect_success()


class TestSearch:
    async def test_one_search(
        self, interval: Interval, page: BrowserPage, transactions: Transaction
    ):
        @interval.action
        async def search(io: IO):
            class Option(RenderableSearchResult):
                value: Union[str, bool, date]
                extraData: NotRequired[int]

            options: list[Option] = [
                {"label": True, "value": True, "extraData": 1},
                {
                    "label": date(2022, 6, 20),
                    "value": date(2022, 6, 20),
                    "extraData": 2,
                },
                {"label": "Viewer", "value": "c", "extraData": 3},
            ]

            async def handle_search(query: str):
                return [o for o in options if query in str(o["label"]).lower()]

            selected = await io.search(
                "Find something",
                initial_results=options,
                render_result=lambda o: o,
                on_search=handle_search,
            )

            return {**selected}

        await transactions.console()
        await transactions.run("search")

        label = page.locator('label:has-text("Find something")')
        await expect(label).to_be_visible()

        await transactions.press_continue()
        await transactions.expect_validation_error()

        inputId = await label.get_attribute("for")
        input = page.locator(f"#{inputId}")
        await input.click()
        await input.fill("view")
        await expect(
            page.locator('[data-pw-search-result]:has-text("true")')
        ).to_be_hidden()
        await expect(
            page.locator('[data-pw-search-result]:has-text("Viewer")')
        ).to_be_visible()
        await page.keyboard.press("ArrowDown")
        await input.press("Enter")
        await expect(
            page.locator('[data-pw-selected-search-result]:has-text("Viewer")')
        ).to_be_visible()
        await transactions.press_continue()
        await transactions.expect_success(
            label="Viewer",
            value="c",
            extraData="3",
        )

    async def test_multi_search(
        self,
        interval: Interval,
        page: BrowserPage,
        transactions: Transaction,
        mock_db: MockDb,
    ):
        def render_user(user: MockDb.User):
            return f"{user['firstName']} {user['lastName']} {({user['email']})}"

        @interval.action
        async def multi_search(io: IO):
            async def handle_search(query: str) -> list[MockDb.User]:
                return mock_db.find_users(query)

            selected = await io.search(
                "Find some users",
                render_result=render_user,
                on_search=handle_search,
            ).multiple()

            return {str(i): render_user(user) for (i, user) in enumerate(selected)}

        await transactions.console()
        await transactions.run("multi_search")

        label = page.locator('label:has-text("Find some users")')
        await expect(label).to_be_visible()

        await transactions.press_continue()
        await transactions.expect_validation_error()

        inputId = await label.get_attribute("for")
        input = page.locator(f"#{inputId}")

        async def search_and_select(query: str):
            await input.click()
            await input.fill(query)
            await expect(page.locator('text="Loading..."')).to_be_visible()
            await expect(page.locator('text="Loading..."')).to_be_hidden()
            await page.click(
                f"[data-pw-search-result]:has-text('{query}'):nth-child(1)"
            )
            await expect(
                page.locator(f".iv-select__multi-value__label:has-text('{query}')")
            ).to_be_visible()
            await expect(
                page.locator(
                    f"[data-pw-search-result]:has-text('{query}'):nth-child(1)"
                )
            ).to_be_hidden()

        await search_and_select("Jacob")
        await search_and_select("Ryan")

        await transactions.press_continue()
        await transactions.expect_success(
            **{
                "0": render_user(mock_db.find_users("Jacob")[0]),
                "1": render_user(mock_db.find_users("Ryan")[0]),
            }
        )

    async def test_optional_multi_search(
        self,
        interval: Interval,
        page: BrowserPage,
        transactions: Transaction,
        mock_db: MockDb,
    ):
        def render_user(user: MockDb.User):
            return f"{user['firstName']} {user['lastName']} {({user['email']})}"

        @interval.action
        async def optional_multi_search(io: IO):
            async def handle_search(query: str) -> list[MockDb.User]:
                return mock_db.find_users(query)

            selected = (
                await io.search(
                    "Find some users",
                    render_result=render_user,
                    on_search=handle_search,
                )
                .multiple()
                .optional()
            )

            if selected is None:
                return "Nothing selected!"

            return {str(i): render_user(user) for (i, user) in enumerate(selected)}

        await transactions.console()
        await transactions.run("optional_multi_search")

        label = page.locator('label:has-text("Find some users")')
        await expect(label).to_be_visible()

        await transactions.press_continue()
        await transactions.expect_success()

        await transactions.restart()
        inputId = await label.get_attribute("for")
        input = page.locator(f"#{inputId}")

        async def search_and_select(query: str):
            await input.click()
            await input.fill(query)
            await expect(page.locator('text="Loading..."')).to_be_visible()
            await expect(page.locator('text="Loading..."')).to_be_hidden()
            await page.click(
                f"[data-pw-search-result]:has-text('{query}'):nth-child(1)"
            )
            await expect(
                page.locator(f".iv-select__multi-value__label:has-text('{query}')")
            ).to_be_visible()
            await expect(
                page.locator(
                    f"[data-pw-search-result]:has-text('{query}'):nth-child(1)"
                )
            ).to_be_hidden()

        await search_and_select("Jacob")
        await search_and_select("Ryan")

        await transactions.press_continue()
        await transactions.expect_success(
            **{
                "0": render_user(mock_db.find_users("Jacob")[0]),
                "1": render_user(mock_db.find_users("Ryan")[0]),
            }
        )

    async def test_two_searches(
        self,
        interval: Interval,
        page: BrowserPage,
        transactions: Transaction,
    ):
        @interval.action
        async def two_searches(io: IO):
            class Option(RenderableSearchResult):
                value: Union[date, bool, str]
                extraData: int

            options: list[Option] = [
                {
                    "label": True,
                    "value": True,
                    "extraData": 1,
                },
                {
                    "label": date(2022, 6, 20),
                    "value": date(2022, 6, 20),
                    "extraData": 2,
                },
                {
                    "label": "Viewer",
                    "value": "c",
                    "extraData": 3,
                },
            ]

            async def handle_search(query: str):
                return [o for o in options if query in str(o["label"]).lower()]

            [r1, r2] = await io.group(
                io.search("First", on_search=handle_search, render_result=lambda o: o),
                io.search("Second", on_search=handle_search, render_result=lambda o: o),
            )

            return {
                "r1": r1["label"],
                "r2": r2["label"],
                "equal": r1 == r2,
                "r1Index": options.index(r1),
                "r2Index": options.index(r2),
                "equalIndex": options.index(r1) == options.index(r2),
            }

        await transactions.console()
        await transactions.run("two_searches")

        label1 = page.locator('label:has-text("First")')
        label2 = page.locator('label:has-text("Second")')

        inputId1 = await label1.get_attribute("for")
        inputId2 = await label2.get_attribute("for")
        input1 = page.locator(f"#{inputId1}")
        input2 = page.locator(f"#{inputId2}")
        await input1.click()
        await input1.fill("view")
        await expect(
            page.locator('[data-pw-search-result]:has-text("Viewer"):nth-child(1)')
        ).to_be_visible()
        await page.keyboard.press("ArrowDown")
        await input1.press("Enter")
        await expect(
            page.locator('[data-pw-selected-search-result]:has-text("Viewer")')
        ).to_be_visible()

        await input2.click()
        for i in range(3):
            await input2.fill("abc")
            await expect(page.locator('text="Loading..."')).to_be_visible()
            await expect(page.locator('text="No results found."')).to_be_visible()
            await input2.fill("fdsa")
            await expect(page.locator('text="Loading..."')).to_be_visible()
            await expect(page.locator('text="No results found."')).to_be_visible()

        await input2.fill("viewer")
        await expect(
            page.locator('[data-pw-search-result]:has-text("Viewer"):nth-child(1)')
        ).to_be_visible()
        await page.keyboard.press("ArrowDown")
        await expect(
            page.locator('[data-pw-search-result]:has-text("Viewer"):nth-child(1)')
        ).to_have_attribute("data-pw-search-result-focused", "true")
        await input2.press("Enter")

        await transactions.press_continue()
        await transactions.expect_success(
            r1="Viewer",
            r2="Viewer",
            equal="true",
            equalIndex="true",
        )


async def test_logs(interval: Interval, page: BrowserPage, transactions: Transaction):
    @interval.action
    async def logs():
        ctx = action_ctx_var.get()
        for i in range(10):
            await ctx.log("Log number", i)

        await asyncio.sleep(0.5)

    await transactions.console()
    await transactions.run("logs")

    await transactions.expect_success()
    log_divs = page.locator("[data-pw-transaction-logs] div")
    for i in range(10):
        await expect(log_divs.nth(i)).to_contain_text(f"Log number {i}")


async def test_error(interval: Interval, page: BrowserPage, transactions: Transaction):
    @interval.action
    async def error(io: IO):
        await io.input.text("First name")
        raise Exception("Unauthorized")

    await transactions.console()
    await transactions.run("error")
    await page.click("text=First name")
    await page.fill('input[type="text"]', "Interval")
    await transactions.press_continue()
    await transactions.expect_failure(message="Unauthorized")


async def test_loading(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    items_in_queue = 5

    @interval.action
    async def loading():
        ctx = action_ctx_var.get()

        await asyncio.sleep(0.5)
        await ctx.loading.start("Bare title")
        await asyncio.sleep(0.5)
        await ctx.loading.update(description="Description text")
        await asyncio.sleep(0.5)
        await ctx.loading.start()
        await asyncio.sleep(0.5)
        await ctx.loading.update(description="Description only")
        await asyncio.sleep(0.5)
        await ctx.loading.update(
            title="With progress",
            items_in_queue=items_in_queue,
        )
        await asyncio.sleep(0.5)
        for i in range(items_in_queue):
            await ctx.loading.complete_one()
            await asyncio.sleep(0.5)

    await transactions.console()
    await transactions.run("loading")

    await expect(page.locator('[data-pw-title]:has-text("Bare title")')).to_be_visible()
    await expect(page.locator("[data-pw-description]")).to_be_hidden()

    await expect(
        page.locator('[data-pw-description]:has-text("Description text")')
    ).to_be_visible()

    await expect(page.locator("[data-pw-description]")).to_be_hidden()
    await expect(page.locator("[data-pw-title]")).to_be_hidden()

    await expect(
        page.locator('[data-pw-description]:has-text("Description only")')
    ).to_be_visible()
    await expect(page.locator("[data-pw-title]")).to_be_hidden()

    await expect(
        page.locator('[data-pw-title]:has-text("With progress")')
    ).to_be_visible()

    for i in range(items_in_queue):
        await expect(page.locator(f"text=Completed {i} of 5")).to_be_visible()


# The `before_listen` and `after_listen` tests from JS are basically
# performed in all tests with the current isolated testing model


async def test_self_destructing(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action
    async def self_destructing():
        interval.routes.remove("self_destructing")
        return "Goodbye!"

    await transactions.console()
    await transactions.run("self_destructing")
    await transactions.expect_success()
    await page.wait_for_timeout(0.2)
    await transactions.console()
    await expect(page.locator("[data-pw-run-slug='self_destructing']")).to_be_hidden()


class TestRedirects:
    async def test_url(
        self,
        interval: Interval,
        page: BrowserPage,
        transactions: Transaction,
    ):
        @interval.action
        async def redirect_url(io: IO, ctx: ActionContext):
            url = (await io.input.url("Enter a URL")).geturl()
            await ctx.redirect(url=url)
            return {"url": url}

        await transactions.console()
        await transactions.run("redirect_url")
        url = "https://interval.com/"

        await page.fill("text=Enter a URL", url)
        await transactions.press_continue()
        await page.wait_for_url(url)

    async def test_route(
        self,
        interval: Interval,
        page: BrowserPage,
        transactions: Transaction,
    ):
        @interval.action
        async def redirect_route(io: IO, ctx: ActionContext):
            [route, params_str] = await io.group(
                io.input.text("Action slug"),
                io.input.text("Params", multiline=True).optional(),
            )

            params = json.loads(params_str) if params_str is not None else None

            await ctx.redirect(route=route, params=params)

        @interval.action
        async def redirect_dest():
            ctx = ctx_var.get()
            return ctx.params

        await transactions.console()
        await transactions.run("redirect_route")
        message = "Hello, from a redirect!"

        await page.fill("text=Action slug", "redirect_dest")
        await page.fill("text=Params", json.dumps({"message": message}))
        await transactions.press_continue()
        await page.wait_for_url(re.compile("redirect_dest"))
        await transactions.expect_success(message=message)


class TestUnlisted:
    async def test_action(
        self,
        interval: Interval,
        page: BrowserPage,
        transactions: Transaction,
    ):
        @interval.action(unlisted=True)
        async def unlisted_action():
            return "Hello, world!"

        await asyncio.sleep(0.5)  # wait for interval to initialize new action
        await transactions.console()
        await expect(
            page.locator('[data-pw-run-slug="unlisted_action"]')
        ).to_be_hidden()
        await page.goto(f"{transactions.config.console_url()}/unlisted_action")
        await transactions.expect_success()

    async def test_page(
        self,
        interval: Interval,
        page: BrowserPage,
        transactions: Transaction,
    ):
        unlisted_page = Page("Unlisted page", unlisted=True)

        @unlisted_page.action
        async def unlisted_listed():
            return "Hello, world!"

        interval.routes.add("unlisted_page", unlisted_page)

        await asyncio.sleep(0.5)  # wait for interval to initialize new action
        await transactions.console()
        await expect(page.locator('[data-pw-run-slug="unlisted_page"]')).to_be_hidden()
        await page.goto(f"{transactions.config.console_url()}/unlisted_page")
        await expect(page.locator('h2:has-text("Unlisted page")')).to_be_visible()
        await transactions.run("unlisted_page/unlisted_listed")
        await transactions.expect_success()


class TestPages:
    def init_users(self, interval: Interval, mock_db: MockDb):
        users = Page("Users")

        @users.handle
        async def handler(display: IO.Display):
            return Layout(
                title="Users",
                menu_items=[
                    {
                        "label": "View funnel",
                        "route": "users/view_funnel",
                    },
                    {"label": "Create user", "route": "users/create"},
                ],
                children=[display.table("Users", data=mock_db.get_users())],
            )

        @users.action
        async def view_funnel():
            io = io_var.get()
            await io.display.markdown("# 🌪️")

        interval.routes.add("users", users)

    @pytest.mark.xdist_group("users")
    async def test_handler(
        self,
        interval: Interval,
        page: BrowserPage,
        transactions: Transaction,
        mock_db: MockDb,
    ):
        self.init_users(interval, mock_db)
        await transactions.console()
        await transactions.navigate("users")

        await expect(page.locator('h2:text("Users")')).to_be_visible()
        await expect(page.locator(".iv-table")).to_be_visible()
        await expect(page.locator("text=of 313").nth(0)).to_be_visible()

    @pytest.mark.xdist_group("users")
    async def test_sub_action(
        self,
        interval: Interval,
        page: BrowserPage,
        transactions: Transaction,
        mock_db: MockDb,
    ):
        self.init_users(interval, mock_db)
        await transactions.console()
        await transactions.navigate("users")
        await expect(
            page.locator(
                "a[href='/dashboard/test-runner/develop/actions/users/view_funnel']:has-text('View funnel')"
            )
        ).to_be_visible()
        await transactions.run("users/view_funnel")

        await expect(page.locator("h2:text('View funnel')")).to_be_visible()
        await expect(page.locator("text=🌪️")).to_be_visible()
        await transactions.press_continue()
        await transactions.expect_success()


async def test_optional(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action
    async def optional(io: IO):
        await io.input.text("Text").optional()
        await io.input.email("Email").optional()
        await io.input.number("Number").optional()
        await io.input.rich_text("Rich text").optional()
        await io.input.date("Date").optional()
        await io.input.time("Time").optional()
        await io.input.datetime("Datetime").optional()

        await io.select.single("Select single", options=[]).optional()
        await io.select.multiple("Select multiple", options=[]).optional()

        async def handle_search(_: str):
            return []

        await io.search(
            "Search", on_search=handle_search, render_result=lambda x: ""
        ).optional()

        d = await io.input.date("Date").optional()
        dt = await io.input.datetime("Datetime").optional()
        table = await io.select.table(
            "Table",
            data=[
                {"a": 1, "b": 2, "c": 3},
                {"a": 4, "b": 5, "c": 6},
                {"a": 7, "b": 8, "c": 9},
            ],
            min_selections=1,
            max_selections=1,
        ).optional()

        await io.display.object(
            "Date",
            data={
                "py_date": d,
            }
            if d is not None
            else None,
        )
        await io.display.object(
            "Datetime",
            data={
                "py_date": dt,
            }
            if dt is not None
            else None,
        )

        return table[0] if table is not None else None

    await transactions.console()
    await transactions.run("optional")

    fields = [
        "Text",
        "Email",
        "Number",
        "Rich text",
        "Date",
        "Time",
        "Datetime",
        "Select single",
        "Select multiple",
        "Search",
    ]

    for field in fields:
        if field == "Rich text":
            await page.locator("div.ProseMirror").click()
        elif field == "Select single" or field == "Search":
            await page.locator(f"label:has-text('{field}')").click()
        else:
            await page.locator(f"text={field}").click()

        for item in await page.locator(":focus").all():
            await item.blur()

        await expect(page.locator('[data-pw="input-error"]')).not_to_be_visible()
        await transactions.press_continue()

    await expect(page.locator('text="Date"')).to_be_visible()
    await input_date(page)
    await transactions.press_continue()
    await expect(page.locator('text="Datetime"')).to_be_visible()
    await input_date(page)
    await input_time(page)
    await transactions.press_continue()
    await page.locator('[role="cell"]:has-text("5")').click()
    await transactions.press_continue()

    await expect(page.locator('text="Date"')).to_be_visible()
    await expect(page.locator("text=py_date")).to_be_visible()
    await transactions.press_continue()
    await expect(page.locator('text="Datetime"')).to_be_visible()
    await expect(page.locator("text=py_date")).to_be_visible()
    await transactions.press_continue()
    await transactions.expect_success(
        a="4",
        b="5",
        c="6",
    )


async def test_notifications(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action
    async def notifications(io: IO, ctx: ActionContext):
        await ctx.notify(
            title="Explicit",
            message="Message",
            delivery=[{"to": "alex@interval.com", "method": "EMAIL"}],
        )

        await io.display.markdown("Press continue to send another")

        await ctx.notify(
            message="Implicit", delivery=[{"to": "test-runner@interval.com"}]
        )

    await transactions.console()
    await transactions.run("notifications")

    controlPanel = page.locator("[data-pw-control-panel]")
    expanded = (await controlPanel.get_attribute("data-pw-expanded")) == "true"
    selected = await controlPanel.get_attribute("data-pw-selected")

    if not expanded or selected != "Notifications":
        await controlPanel.locator('[data-pw-tab-id="Notifications"]').click()

    await expect(controlPanel.locator("text=Explicit: Message")).to_be_visible()
    await expect(
        controlPanel.locator("text=Would have sent to alex@interval.com via EMAIL")
    ).to_be_visible()

    await transactions.press_continue()

    await expect(controlPanel.locator("text=Implicit")).to_be_visible()
    await expect(
        controlPanel.locator("text=Would have sent to test-runner@interval.com")
    ).to_be_visible()


async def test_malformed(
    interval: Interval, page: BrowserPage, transactions: Transaction
):
    @interval.action
    async def malformed(io: IO):
        await io.input.text(Exception())  # type: ignore

    await transactions.console()
    await transactions.run("malformed")
    await expect(page.locator("text=ValidationError")).to_be_visible()
