"""
Content extraction from report pages.

Extracts title, HTML content, and text content from portal pages.
"""

from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright.async_api import Page
from src.config import Config
from src.utils.logger import get_logger
from src.utils.exceptions import ExtractionError

logger = get_logger(__name__)


class ContentExtractor:
    """Extracts content from report pages."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize content extractor.

        Args:
            config: Config instance (uses default if not provided)
        """
        self.config = config or Config()

    async def extract_content(self, page: Page, url: str) -> Dict[str, Any]:
        """
        Extract content from report page.

        Args:
            page: Playwright page object
            url: Target report URL

        Returns:
            Dict with title, html_content, text_content
        """
        try:
            # Navigate to report URL
            logger.info(f"Navigating to report URL: {url}")
            await page.goto(
                url,
                wait_until="networkidle",
                timeout=self.config.page_load_timeout * 1000,
            )

            # Extract title
            title = await self._extract_title(page)

            # Extract HTML content
            html_content = await self._extract_html_content(page)

            # Extract text content
            text_content = await self._extract_text_content(page)

            logger.info(
                f"Content extracted successfully from {url}",
                extra={"title_length": len(title), "html_length": len(html_content)},
            )

            return {
                "title": title,
                "html_content": html_content,
                "text_content": text_content,
            }

        except Exception as e:
            logger.error(f"Content extraction failed: {e}", extra={"url": url})
            raise ExtractionError(f"Failed to extract content: {e}", context={"url": url})

    async def _extract_title(self, page: Page) -> str:
        """
        Extract page title from article h2 selector.

        Args:
            page: Playwright page object

        Returns:
            Title text or empty string if not found
        """
        try:
            # Wait for element visibility
            locator = page.locator(self.config.title_selector)
            await locator.wait_for(state="visible", timeout=self.config.page_load_timeout * 1000)

            # Extract text content
            title = await locator.text_content()
            return title.strip() if title else ""

        except Exception as e:
            logger.warning(f"Failed to extract title: {e}")
            return ""

    async def _extract_html_content(self, page: Page) -> str:
        """
        Extract and clean HTML content.

        Args:
            page: Playwright page object

        Returns:
            Cleaned HTML content
        """
        try:
            # Get content element
            locator = page.locator(self.config.content_container_selector)

            # Extract inner HTML
            html = await locator.inner_html()

            # Clean script tags
            cleaned_html = self._clean_scripts(html)

            return cleaned_html if cleaned_html else ""

        except Exception as e:
            logger.warning(f"Failed to extract HTML content: {e}")
            return ""

    async def _extract_text_content(self, page: Page) -> str:
        """
        Extract plain text content.

        Args:
            page: Playwright page object

        Returns:
            Plain text content
        """
        try:
            # Get content element
            locator = page.locator(self.config.content_container_selector)

            # Extract inner text
            text = await locator.inner_text()

            return text.strip() if text else ""

        except Exception as e:
            logger.warning(f"Failed to extract text content: {e}")
            return ""

    @staticmethod
    def _clean_scripts(html: str) -> str:
        """
        Remove script tags from HTML.

        Args:
            html: HTML string

        Returns:
            Cleaned HTML with script tags removed
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Remove all script tags
            for script in soup.find_all("script"):
                script.decompose()

            return str(soup)

        except Exception as e:
            logger.error(f"Error cleaning scripts from HTML: {e}")
            return html
