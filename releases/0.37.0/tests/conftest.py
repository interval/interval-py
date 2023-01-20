# pylint: disable=redefined-outer-name

import asyncio
from typing import AsyncIterator
from faker import Faker

import pytest
from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)

from tests.data.mock_db import MockDb

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

    await page.close()


@pytest.fixture
def transactions(page: Page, config: Config) -> Transaction:
    return Transaction(page=page, config=config)


@pytest.fixture
def mock_db(faker: Faker) -> MockDb:
    return MockDb(faker)


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    yield loop
