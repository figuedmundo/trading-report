from playwright.async_api import async_playwright
from .config import WEBSITE_USERNAME, WEBSITE_PASSWORD

async def login_and_fetch_report(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await (await browser.new_context()).new_page()
        await page.goto(url)
        if await page.query_selector('input[type="password"]'):
            await page.fill('input[type="text"]', WEBSITE_USERNAME)
            await page.fill('input[type="password"]', WEBSITE_PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
        html = await page.content()
        await browser.close()
        return html
