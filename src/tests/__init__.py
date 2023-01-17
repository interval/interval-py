from dataclasses import dataclass
from typing import Optional

from playwright.async_api import BrowserContext, Page, expect


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

    def console_url(self) -> str:
        return self.dashboard_url("develop/actions")

    async def log_in(self, context: BrowserContext):
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


class Transaction:
    page: Page
    config: Config

    def __init__(self, page: Page, config: Config):
        self.page = page
        self.config = config

    async def console(self):
        await self.page.goto(self.config.console_url())

    async def navigate(self, page_slug: str):
        await self.page.click(f"[data-pw-action-group='{page_slug}']")

    async def run(self, slug: str):
        print("Starting test", slug)
        await self.page.click(f"[data-pw-run-slug='{slug}']")

    async def press_continue(self, label: str = "Continue"):
        await self.page.click(f'button:has-text("{label}")')

    async def restart(self):
        await self.page.locator("button:has-text('New transaction')").click()
        await self.page.wait_for_load_state("networkidle")

    async def expect_validation_error(self, message: str = "This field is required"):
        await expect(
            self.page.locator(f"[data-pw='field-error']:has-text('{message}')")
        ).to_be_visible()

    async def expect_result(self, **kwargs: str):
        for key, val in kwargs.items():
            await expect(
                self.page.locator('[data-test-id="transaction-result"]')
            ).to_contain_text("".join([key, val]))

    async def expect_success(self, **kwargs: str):
        await expect(
            self.page.locator('[data-test-id="result-type"]:has-text("Success")')
        ).to_be_visible()

        if len(kwargs) is not None:
            await self.expect_result(**kwargs)

    async def expect_failure(
        self, message: Optional[str] = None, error: Optional[str] = None
    ):
        await expect(
            self.page.locator('[data-test-id="result-type"]:has-text("Error")')
        ).to_be_visible()

        if message is not None:
            await expect(
                self.page.locator('[data-test-id="transaction-result"]')
            ).to_contain_text(message)

        if error is not None:
            await expect(
                self.page.locator('[data-test-id="transaction-result"]')
            ).to_contain_text(error)


base_config = Config(
    url="http://localhost:3000",
    login=Config.Login(
        email="test-runner@interval.com",
        password="password",
    ),
    api_key="d790283e-d845-48f6-95f2-27c8a7119b16",
    live_api_key="live_test_runner_test_api_key",
)
