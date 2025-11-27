"""
Browser lifecycle management and authentication handling.

Provides BrowserManager class for context manager pattern and login flow.
"""

import asyncio
import time
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from src.config import Config
from src.utils.logger import get_logger
from src.utils.exceptions import LoginError, CredentialError

logger = get_logger(__name__)


class BrowserManager:
    """Manages browser lifecycle with async context manager pattern."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize browser manager.

        Args:
            config: Config instance (uses default if not provided)
        """
        self.config = config or Config()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.request_id: Optional[str] = None

    async def __aenter__(self) -> "BrowserManager":
        """
        Async context manager entry: launch browser.

        Returns:
            Self for use in with statement
        """
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.playwright_headless,
            args=self.config.browser_args,
        )
        self.context = await self.browser.new_context(
            viewport={
                "width": self.config.browser_viewport_width,
                "height": self.config.browser_viewport_height,
            },
            user_agent=self.config.user_agent,
        )
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Async context manager exit: cleanup browser.

        Ensures browser always closes, even if errors occur.
        """
        try:
            if self.page:
                await self.page.close()
        except Exception as e:
            logger.error(f"Error closing page: {e}")

        try:
            if self.context:
                await self.context.close()
        except Exception as e:
            logger.error(f"Error closing context: {e}")

        try:
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error stopping playwright: {e}")

    async def needs_login(self) -> bool:
        """
        Check if page requires login.

        Returns:
            True if login required, False otherwise
        """
        if not self.page:
            raise RuntimeError("Page not initialized")

        try:
            # Check for login input field
            login_input = await self.page.query_selector(self.config.username_selector)
            return login_input is not None
        except Exception as e:
            logger.error(f"Error checking login requirement: {e}")
            return False

    async def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        """
        Perform login with retry logic.

        Args:
            username: Portal username (uses config default if not provided)
            password: Portal password (uses config default if not provided)

        Returns:
            True if login successful, False otherwise

        Raises:
            CredentialError: If credentials missing
            LoginError: If login fails after retries
        """
        if not self.page:
            raise RuntimeError("Page not initialized")

        # Use provided credentials or fallback to config
        username = username or self.config.trading_portal_username
        password = password or self.config.trading_portal_password

        # Validate credentials present
        if not username or not password:
            raise CredentialError(
                "Portal credentials required but not provided",
                context={"url": self.config.login_url},
            )

        # Navigate to login page
        try:
            await self.page.goto(
                self.config.login_url,
                wait_until="networkidle",
                timeout=self.config.login_timeout * 1000,
            )
        except Exception as e:
            raise LoginError(
                f"Failed to navigate to login page: {e}",
                context={"url": self.config.login_url},
            )

        # Retry logic with exponential backoff
        backoff_delays = [1, 2, 4]  # seconds
        last_error = None

        for attempt in range(self.config.max_login_retries):
            try:
                logger.info(f"Login attempt {attempt + 1}/{self.config.max_login_retries}")

                # Fill login form
                await self.page.fill(self.config.username_selector, username)
                await self.page.fill(self.config.password_selector, password)

                # Submit form
                await self.page.click(self.config.submit_selector)

                # Wait for navigation completion
                await self.page.wait_for_load_state(
                    "networkidle",
                    timeout=self.config.login_timeout * 1000,
                )

                logger.info("Login successful")
                return True

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Login attempt {attempt + 1} failed: {e}",
                    extra={"attempt": attempt + 1},
                )

                # Apply backoff delay if not last attempt
                if attempt < self.config.max_login_retries - 1:
                    delay = backoff_delays[attempt]
                    logger.info(f"Waiting {delay}s before retry")
                    await asyncio.sleep(delay)

        # All retries exhausted
        raise LoginError(
            f"Login failed after {self.config.max_login_retries} attempts: {last_error}",
            context={"last_error": str(last_error)},
        )
