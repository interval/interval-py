import asyncio

import pytest
from playwright.async_api import Page, expect

from interval_py import Interval, IO, ActionContext

from . import base_config, Transaction


@pytest.fixture(scope="session", autouse=True)
async def host(event_loop: asyncio.AbstractEventLoop):
    interval = Interval(
        api_key=base_config.api_key,
        endpoint=base_config.endpoint_url,
        log_level="debug",
    )

    @interval.action_with_slug("io.display.heading")
    async def io_display_heading(io: IO):
        await io.display.heading("io.display.heading result")

    @interval.action
    async def context(_: IO, ctx: ActionContext):
        return {
            "user": f"{ctx.user.first_name} {ctx.user.last_name}",
            "message": ctx.params.get("message", None),
            "environment": ctx.environment,
        }

    @interval.action_with_slug("io.group")
    async def io_group(io: IO):
        await io.group(
            io.display.markdown("1. First item"),
            io.display.markdown("2. Second item"),
        )

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
                },
            )
        )

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
