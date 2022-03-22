import os
from dataclasses import dataclass

from playwright.async_api import Playwright, Page, expect


@dataclass
class Config:
    @dataclass
    class Login:
        email: str
        password: str

    url: str
    login: Login
    api_key: str
    live_api_key: str

    def app_url(self, path: str) -> str:
        if path.startswith("/"):
            path = path[1:]
        return f"{self.url}/{path}"

    @property
    def endpoint_url(self) -> str:
        return f"{self.url.replace('http', 'ws')}/websocket"

    def dashboard_url(self, path: str = "", org_slug: str = "test-runner"):
        if path.startswith("/"):
            path = path[1:]

        return self.app_url(f"/dashboard/{org_slug}/{path}")

    async def log_in(self, playwright: Playwright):
        browser = await playwright.chromium.launch(headless=(not os.getenv("HEADED")))
        context = await browser.new_context()
        page = await context.new_page()

        print("Logging in...")
        await page.goto(self.app_url("/login"))
        await page.fill('input[name="email"]', self.login.email)
        await page.click('button[type="submit"]')
        await page.fill('input[name="password"]', self.login.password)
        async with page.expect_navigation():
            await page.click('button[type="submit"]')
        print("Logged in!")

        return page


@dataclass
class Transaction:
    page: Page

    async def console(self):
        await self.page.goto(base_config.dashboard_url("develop/console"))

    async def run(self, slug: str):
        print("Starting test", slug)
        await self.page.locator(f"[data-pw-run-slug='{slug}']").click()

    async def press_continue(self):
        await self.page.locator('button:has-text("Continue")').click()

    async def expect_result(self, result: dict[str, str]):
        for key, val in result.items():
            await expect(
                self.page.locator('[data-test-id="transaction-result"]')
            ).to_contain_text("".join([key, val]))

    async def expect_success(self, result: dict[str, str] | None = None):
        await expect(
            self.page.locator('[data-test-id="result-type"]:has-text("Success")')
        ).to_be_visible()

        if result is not None:
            await self.expect_result(result)

    async def expect_failure(self, result: dict[str, str] | None = None):
        await expect(
            self.page.locator('[data-test-id="result-type"]:has-text("Error")')
        ).to_be_visible()

        if result is not None:
            await self.expect_result(result)


base_config = Config(
    url="http://localhost:3000",
    login=Config.Login(
        email="test-runner@interval.com",
        password="password",
    ),
    api_key="d790283e-d845-48f6-95f2-27c8a7119b16",
    live_api_key="live_test_runner_test_api_key",
)