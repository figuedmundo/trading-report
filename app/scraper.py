import asyncio
import logging
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page
from typing import Optional, Dict, Any, List
from .config import Config

logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = await self.browser.new_page(user_agent=Config.USER_AGENT)
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def scrape_report(self, url: str) -> Dict[str, Any]:
        """
        Scrape market report from secure website
        """
        try:
            logger.info(f"Starting scrape for URL: {url}")
            
            # Navigate to the URL
            response = await self.page.goto("https://protradingskills.com/wp-login.php", wait_until="networkidle", timeout=60000)
            
            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")
            
            # Check if login is required
            if await self._needs_login():
                await self._handle_login()
            
            # Wait for content to load
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # Additional wait for dynamic content
            
            # Extract content
            content = await self._extract_content(url)
            
            logger.info("Successfully scraped report content")
            return {
                "success": True,
                "url": url,
                "title": content.get("title"),
                "html_content": content.get("html"),
                "text_content": content.get("text"),
                "report_images": content.get("images")
            }
            
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "html_content": "",
                "text_content": "",
                "report_images": []
            }
    
    async def _needs_login(self) -> bool:
        """Check if the page requires login"""
        login_input = await self.page.query_selector('input[id="user_login"]')
        return login_input is not None

    async def _handle_login(self):
        """Handle login process with multiple fallback strategies"""
        username = Config.PRO_USERNAME
        password = Config.PRO_PASSWORD
        
        if not username or not password:
            raise Exception("Username and password required for login")
        
        await self.page.fill('input[id="user_login"]', username)
        await self.page.fill('input[id="user_pass"]', password)
        await self.page.click('input[id="wp-submit"]')
                   
        # Wait for navigation after login
        await self.page.wait_for_load_state('networkidle', timeout=60000)
        return True
    
    async def _extract_content(self, report_url) -> Dict[str, Any]:
        """Extract content from the page"""
        try:
            # Go to the report page
            await self.page.goto(report_url, wait_until="networkidle", timeout=100000)

            # Get page title
            await self.page.locator("article h2").wait_for(state='visible', timeout=100000)
            title = await self.page.locator("article h2").text_content()
            
            # Content extraction strategies
            content_element = self.page.locator("div.entry-content")
            
            html_content = await content_element.inner_html()
            html_content = self._clean_scripts(html_content)
            text_content = await content_element.inner_text()
            images = self._get_images(html_content)

            return {
                "title": title,
                "html": html_content,
                "text": text_content,
                "images": images
            }
            
        except Exception as e:
            logger.error(f"Content extraction failed: {e}")
            return {
                "title": "Extraction Failed",
                "html": "",
                "text": "",
                "images": []
            }
        
    def _get_images(self, html_report) -> List[str]:
        soup = BeautifulSoup(html_report, "html.parser")

        # Extract external image URLs
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                images.append(src)

        return images
    
    def _clean_scripts(self, html): 
        # Parse the HTML
        soup = BeautifulSoup(html, 'html.parser')

        # Remove all <script> tags and their contents
        for script in soup.find_all('script'):
            script.decompose()

        # Cleaned HTML
        return str(soup)

def scrape_report_wrapper(url: str) -> Dict[str, Any]:
    """Synchronous wrapper for async scraping"""
    async def _scrape():
        async with WebScraper() as scraper:
            return await scraper.scrape_report(url)
    
    return asyncio.run(_scrape())
