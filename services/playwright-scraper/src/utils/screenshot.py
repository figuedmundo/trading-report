"""
Full-page screenshot capture and encoding.

Takes and encodes browser screenshots as base64.
"""

import base64
from typing import Optional
from playwright.async_api import Page
from src.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def capture_screenshot(page: Page, config: Optional[Config] = None) -> str:
    """
    Capture full-page screenshot and encode to base64.

    Args:
        page: Playwright page object
        config: Config instance (optional)

    Returns:
        Data URI string with base64 encoded screenshot
    """
    try:
        # Take full-page screenshot
        screenshot_bytes = await page.screenshot(full_page=True)

        # Encode to base64
        base64_data = base64.b64encode(screenshot_bytes).decode("utf-8")

        # Create data URI
        data_uri = f"data:image/png;base64,{base64_data}"

        logger.info("Screenshot captured successfully")
        return data_uri

    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        return ""
