from playwright.async_api import async_playwright
from .config import WEBSITE_USERNAME, WEBSITE_PASSWORD

async def login_and_fetch_report(report_url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await (await browser.new_context()).new_page()
        await page.goto("https://protradingskills.com/wp-login.php")

        if await page.query_selector('input[id="user_login"]'):
            await page.fill('input[id="user_login"]', WEBSITE_USERNAME)
            await page.fill('input[id="user_pass"]', WEBSITE_PASSWORD)
            await page.click('input[id="wp-submit"]')
            await page.wait_for_load_state('networkidle')
            await page.goto(report_url)
            await page.wait_for_load_state('networkidle')
            await page.locator("article h2").wait_for(state='visible')
            
        content = await page.locator("div.entry-content").text_content()

        await browser.close()
        return content
