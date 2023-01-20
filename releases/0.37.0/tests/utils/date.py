from playwright.async_api import Page, expect

from .. import Transaction


async def input_date(page: Page):
    input = page.locator('.iv-datepicker input[type="text"]')
    await input.click()
    await page.wait_for_timeout(
        200
    )  # wait for 100ms delay we apply before showing the popover
    await input.fill("02/22/2022")
    await page.locator('.flatpickr-day:has-text("25")').click()
    await expect(input).to_have_value("02/25/2022")


async def input_invalid_date(page: Page, transactions: Transaction):
    input = page.locator('.iv-datepicker input[type="text"]')
    await input.click()
    await page.wait_for_timeout(
        200
    )  # wait for 100ms delay we apply before showing the popover
    await input.fill("12/34/5678")
    await input.press("Tab")
    await transactions.press_continue()
    await transactions.expect_validation_error("Please enter a valid date.")


async def input_time(page: Page):
    await expect(page.locator(".iv-datepicker")).to_be_visible()
    selects = page.locator(".iv-datepicker select")

    [h, m, ampm] = [selects.nth(0), selects.nth(1), selects.nth(2)]

    await h.select_option(value="2")
    await h.press("Tab")

    await expect(m).to_be_focused()
    await m.type("36")
    await m.press("Tab")

    await expect(ampm).to_be_focused()
    await ampm.select_option("pm")
    # Note: keyboard navigation does not seem to work here.
    # ampm.press('ArrowDown') or page.keyboard.press('ArrowDown') doesn't move the selection to 'PM'.
