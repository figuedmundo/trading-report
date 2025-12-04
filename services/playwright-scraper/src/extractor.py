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
        Extract page title from article h2 selector with fallback strategies.

        Args:
            page: Playwright page object

        Returns:
            Title text or empty string if not found
        """
        # Try multiple selectors in order of preference
        selectors = [
            self.config.title_selector,  # article h2
            "h1.entry-title",  # WordPress common
            "h1",  # Generic H1
            "article h1",  # Article H1
            "title",  # Page title as last resort
        ]

        for selector in selectors:
            try:
                locator = page.locator(selector).first
                title = await locator.text_content(timeout=5000)
                if title and title.strip():
                    logger.info(f"Extracted title using selector: {selector}")
                    return title.strip()
            except Exception:
                continue

        logger.warning("Failed to extract title with all selectors")
        return ""

    async def _extract_html_content(self, page: Page) -> str:
        """
        Extract and clean HTML content with fallback strategies.

        Args:
            page: Playwright page object

        Returns:
            Cleaned HTML content
        """
        # Try multiple selectors in order of preference
        selectors = [
            self.config.content_container_selector,  # div.entry-content
            "article",  # Generic article
            ".post-content",  # Common WordPress
            ".content",  # Generic content
            "main",  # Main content area
            "body",  # Last resort - full page
        ]

        for selector in selectors:
            try:
                locator = page.locator(selector).first
                html = await locator.inner_html(timeout=10000)
                if html and html.strip():
                    # Clean script tags
                    cleaned_html = self._clean_scripts(html)
                    if cleaned_html and len(cleaned_html.strip()) > 100:
                        logger.info(f"Extracted HTML content using selector: {selector} ({len(cleaned_html)} chars)")
                        return cleaned_html
            except Exception:
                continue

        logger.warning("Failed to extract HTML content with all selectors")
        return ""

    async def _extract_text_content(self, page: Page) -> str:
        """
        Extract plain text content with fallback strategies.

        Args:
            page: Playwright page object

        Returns:
            Plain text content
        """
        # Try multiple selectors in order of preference
        selectors = [
            self.config.content_container_selector,  # div.entry-content
            "article",  # Generic article
            ".post-content",  # Common WordPress
            ".content",  # Generic content
            "main",  # Main content area
            "body",  # Last resort - full page
        ]

        for selector in selectors:
            try:
                locator = page.locator(selector).first
                text = await locator.inner_text(timeout=10000)
                if text and text.strip() and len(text.strip()) > 100:
                    logger.info(f"Extracted text content using selector: {selector} ({len(text)} chars)")
                    return text.strip()
            except Exception:
                continue

        logger.warning("Failed to extract text content with all selectors")
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
