import asyncio, os

from playwright.async_api import async_playwright, expect

from interval_py import Interval, IO, ActionContext

from . import config, Transaction

interval = Interval(
    api_key=config.api_key,
    endpoint=config.endpoint_url,
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


loop = asyncio.get_event_loop()
listen = loop.create_task(interval.listen_async())


async def main():
    async with async_playwright() as p:
        page = await config.log_in(p)

        transactions = Transaction(page)

        await transactions.console()
        await transactions.run("io.display.heading")
        await expect(page.locator("text=io.display.heading result")).to_be_visible()
        await transactions.press_continue()
        await transactions.expect_success()

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


loop.run_until_complete(
    asyncio.gather(
        listen,
        main(),
    )
)
