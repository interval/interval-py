# pylint: disable=redefined-outer-name

import asyncio
from typing import AsyncIterator

import pytest
from playwright.async_api import Page, async_playwright

from interval_sdk import Interval

from . import Config, base_config as base_config, Transaction


@pytest.fixture(scope="session")
def config() -> Config:
    return base_config


@pytest.fixture(scope="session")
async def page(config: Config) -> AsyncIterator[Page]:
    async with async_playwright() as p:
        page = await config.log_in(p)
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
