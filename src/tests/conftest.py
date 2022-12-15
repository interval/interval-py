# pylint: disable=redefined-outer-name

import asyncio
from typing import AsyncIterator

import pytest
from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)

from interval_sdk import Interval

from . import Config, base_config as base_config, Transaction


@pytest.fixture(scope="session")
def config() -> Config:
    return base_config


@pytest.fixture(scope="session")
async def playwright() -> AsyncIterator[Playwright]:
    async with async_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
async def context(
    config: Config,
    playwright: Playwright,
    browser_name: str,
    browser_type_launch_args: dict,
) -> AsyncIterator[BrowserContext]:
    # tests_dir = os.path.dirname(os.path.realpath(__file__))
    browser_context_args: dict = {}

    browser_type: BrowserType = getattr(playwright, browser_name)
    browser = await browser_type.launch(
        # tests_dir + "/.session.json",
        **{
            **browser_type_launch_args,
            **browser_context_args,
        }
    )
    context = await browser.new_context()
    await config.log_in(context)
    yield context
    await context.close()


@pytest.fixture(scope="function")
async def page(
    context: BrowserContext,
) -> AsyncIterator[Page]:
    page = await context.new_page()
    yield page


@pytest.fixture
async def interval(config: Config) -> Interval:
    return Interval(
        api_key=config.api_key,
        endpoint=config.endpoint_url,
        log_level="debug",
    )


@pytest.fixture
def transactions(page: Page) -> Transaction:
    return Transaction(page)


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    return asyncio.new_event_loop()
