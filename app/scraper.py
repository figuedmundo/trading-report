# from playwright.async_api import async_playwright
# from .config import WEBSITE_USERNAME, WEBSITE_PASSWORD

# async def login_and_fetch_report(report_url):
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         page = await (await browser.new_context()).new_page()
#         await page.goto("https://protradingskills.com/wp-login.php")

#         if await page.query_selector('input[id="user_login"]'):
#             await page.fill('input[id="user_login"]', WEBSITE_USERNAME)
#             await page.fill('input[id="user_pass"]', WEBSITE_PASSWORD)
#             await page.click('input[id="wp-submit"]')
#             await page.wait_for_load_state('networkidle')
#             await page.goto(report_url)
#             await page.wait_for_load_state('networkidle')
#             await page.locator("article h2").wait_for(state='visible')
            
#         content = await page.locator("div.entry-content").text_content()

#         await browser.close()
#         return content
from playwright.async_api import async_playwright
from app.config import Config
import logging
from typing import Optional

class WebScraper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.username = Config.WEBSITE_USERNAME
        self.password = Config.WEBSITE_PASSWORD
    
    async def fetch_report_content(self, report_url: str) -> str:
        """
        Fetch report content from secured website using Playwright
        """
        self.logger.info(f"Starting to fetch content from: {report_url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                # Navigate to the URL with extended timeout
                await page.goto("https://protradingskills.com/wp-login.php", wait_until='networkidle', timeout=60000)

                if await page.query_selector('input[id="user_login"]'):
                    await page.fill('input[id="user_login"]', WEBSITE_USERNAME)
                    await page.fill('input[id="user_pass"]', WEBSITE_PASSWORD)
                    await page.click('input[id="wp-submit"]')
                    await page.wait_for_load_state('networkidle')
               
                    
                content = await page.locator("div.entry-content").text_content()
                
                # Handle login if required
                if await self._handle_login(page):
                    self.logger.info("Login successful")
                    # Wait for page to load after login
                    await page.wait_for_load_state('networkidle', timeout=30000)
                
                # Get page content
                await page.goto(report_url)
                await page.wait_for_load_state('networkidle')
                await page.locator("article h2").wait_for(state='visible')
                # await page.locator("div.entry-content").text_content()
                # html_content = await page.content()
                html_content = await page.locator("div.entry-content").all_text_contents()
                self.logger.info(f"Successfully fetched report. Length: {len(html_content)}")
                
                return html_content
                
            except Exception as e:
                self.logger.error(f"Error during scraping: {str(e)}")
                # Take screenshot for debugging if possible
                try:
                    await page.screenshot(path='error_screenshot.png')
                    self.logger.info("Error screenshot saved")
                except:
                    pass
                raise e
                
            finally:
                await browser.close()
    
    async def _handle_login(self, page) -> bool:
            if await page.query_selector('input[id="user_login"]'):
                await page.fill('input[id="user_login"]', self.username)
                await page.fill('input[id="user_pass"]', self.password)
                await page.click('input[id="wp-submit"]')
            else:
                self.logger.error(f"Login process failed: {str(e)}")
                raise Exception(f"Login failed: {str(e)}")

            # Wait for navigation after login
            await page.wait_for_load_state('networkidle', timeout=15000)
            
            # Check if login was successful (look for common error indicators)
            page_content = await page.content()
            error_indicators = ['error', 'invalid', 'incorrect', 'failed', 'wrong']
            
            if any(indicator in page_content.lower() for indicator in error_indicators):
                self.logger.warning("Possible login failure detected")
                return False
            
            return True
            
# Global instance
web_scraper = WebScraper()