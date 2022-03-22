import asyncio

import pytest
from playwright.async_api import Page, expect

from interval_py import Interval, IO, ActionContext
from interval_py.io_schema import LabelValue

from . import base_config, Transaction


@pytest.fixture(scope="session", autouse=True)
async def host(event_loop: asyncio.AbstractEventLoop):
    interval = Interval(
        api_key=base_config.api_key,
        endpoint=base_config.endpoint_url,
        log_level="debug",
    )

    @interval.action_with_slug("io.display.heading")
    async def display_heading(io: IO):
        await io.display.heading("io.display.heading result")

    @interval.action
    async def context(_: IO, ctx: ActionContext):
        return {
            "user": f"{ctx.user.first_name} {ctx.user.last_name}",
            "message": ctx.params.get("message", None),
            "environment": ctx.environment,
        }

    @interval.action_with_slug("io.group")
    async def group(io: IO):
        await io.group(
            io.display.markdown("1. First item"),
            io.display.markdown("2. Second item"),
        )

    @interval.action_with_slug("io.display.object")
    async def display_object(io: IO):
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
                },
            )
        )

    @interval.action_with_slug("io.display.table")
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

    @interval.action_with_slug("io.input.text")
    async def io_input_text(io: IO):
        name = await io.input.text("First name")
        return {"name": name}

    @interval.action_with_slug("io.input.number")
    async def input_number(io: IO):
        num = await io.input.number("Enter a number")
        num2 = await io.input.number(
            f"Enter a second number that's greater than {num}", min=num + 1
        )

        return {"sum": num + num2}

    @interval.action_with_slug("io.input.richText")
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

    @interval.action_with_slug("io.select.multiple")
    async def select_multiple(io: IO):
        options: list[LabelValue] = [
            {
                "value": "A",
                "label": "A",
            },
            {
                "value": "B",
                "label": "B",
            },
            {
                "value": "C",
                "label": "C",
            },
        ]

        selected = await io.select.multiple("Select zero or more", options=options)

        selected = await io.select.multiple(
            "Optionally modify the selection", options=options, default_value=selected
        )

        selected_values = [o["value"] for o in selected]

        ret = {}

        for option in options:
            ret[option["label"]] = option["value"] in selected_values

        return ret

    event_loop.create_task(interval.listen_async())

    yield interval


async def test_heading(page: Page, transactions: Transaction):
    await transactions.console()
    await transactions.run("io.display.heading")
    await expect(page.locator("text=io.display.heading result")).to_be_visible()
    await transactions.press_continue()
    await transactions.expect_success()


async def test_context(page: Page, transactions: Transaction):
    await transactions.console()
    await transactions.run("context")
    await page.goto(page.url + "?message=Hello")
    await transactions.expect_success(
        {
            "user": "Test Runner",
            "message": "Hello",
            "environment": "development",
        }
    )


async def test_group(page: Page, transactions: Transaction):
    await transactions.console()
    await transactions.run("io.group")
    await expect(page.locator("text=First item")).to_be_visible()
    await expect(page.locator("text=Second item")).to_be_visible()
    await transactions.press_continue()
    await transactions.expect_success()


async def test_object(page: Page, transactions: Transaction):
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


async def test_table(page: Page, transactions: Transaction):
    await transactions.console()
    await transactions.run("io.display.table")
    await expect(page.locator("text=io.display.table result")).to_be_visible()
    await expect(page.locator('th:has-text("string")')).to_be_visible()
    await expect(page.locator('td:has-text("string")')).to_be_visible()
    await expect(page.locator('th:has-text("number")')).to_be_visible()
    await expect(page.locator('td:has-text("15")')).to_be_visible()
    await expect(page.locator('th:has-text("boolean")')).to_be_visible()
    await expect(page.locator('td:has-text("true")')).to_be_visible()
    await expect(page.locator('th:has-text("none")')).to_be_visible()
    await expect(page.locator('td:has-text("-")')).to_be_visible()
    await transactions.press_continue()
    await transactions.expect_success()


async def test_text(page: Page, transactions: Transaction):
    await transactions.console()
    await transactions.run("io.input.text")

    await page.click("text=First name")
    await page.fill('input[type="text"]', "Interval")
    await transactions.press_continue()
    await transactions.expect_success({"name": "Interval"})


async def test_number(page: Page, transactions: Transaction):
    await transactions.console()
    await transactions.run("io.input.number")

    await page.click("text=Enter a number")
    await page.fill('input[type="number"]', "12")
    await transactions.press_continue()

    await page.click("text=Enter a second number")
    await page.fill('input[type="number"]', "7")
    await expect(
        page.locator('.btn [role="button"]:has-text("Continue")')
    ).to_have_attribute("aria-disabled", "true")
    await page.fill('input[type="number"]', "13")

    await transactions.press_continue()
    await transactions.expect_success({"sum": "25"})


async def test_rich_text(page: Page, transactions: Transaction):
    await transactions.console()
    await transactions.run("io.input.richText")
    await expect(page.locator("text=Email body")).to_be_visible()

    input = page.locator(".ProseMirror")

    await page.select_option('select[title="Heading level"]', "1")
    await input.type("Heading 1")
    await input.press("Enter")
    await page.click('button[title="Toggle italic"]')
    await input.type("Emphasis")
    await input.press("Enter")
    await page.click('button[title="Toggle italic"]')
    await page.click('button[title="Toggle underline"]')
    await input.type("Underline")
    await page.click('button[title="Toggle underline"]')

    await transactions.press_continue()
    await expect(page.locator('h2:has-text("You entered:")')).to_be_visible()
    await expect(page.locator("pre code")).to_contain_text(
        "<h1>Heading 1</h1><p><em>Emphasis</em></p><p><u>Underline</u></p>\n"
    )
    await transactions.press_continue()
    await transactions.expect_success()


async def test_select_multiple(page: Page, transactions: Transaction):
    await transactions.console()
    await transactions.run("io.select.multiple")

    await expect(page.locator("text=Select zero or more")).to_be_visible()
    await page.click('input[type="checkbox"][value="A"]')
    await page.click('input[type="checkbox"][value="C"]')
    await transactions.press_continue()

    await expect(page.locator("text=Optionally modify the selection")).to_be_visible()
    await expect(page.locator('input[type="checkbox"][value="A"]')).to_be_checked()
    await expect(page.locator('input[type="checkbox"][value="C"]')).to_be_checked()
    await page.click('input[type="checkbox"][value="C"]')
    await transactions.press_continue()

    await transactions.expect_success(
        {
            "A": "true",
            "B": "false",
            "C": "false",
        }
    )
