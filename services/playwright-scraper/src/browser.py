"""
Browser lifecycle management and authentication handling.

Provides BrowserManager class for context manager pattern and login flow.
"""

import asyncio
import time
import random
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from camoufox.async_api import AsyncCamoufox
from src.config import Config
from src.utils.logger import get_logger
from src.utils.exceptions import LoginError, CredentialError

logger = get_logger(__name__)


class BrowserManager:
    """Manages browser lifecycle using Camoufox for Cloudflare bypass."""

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
        Async context manager entry: launch Camoufox browser.

        Returns:
            Self for use in with statement
        """
        logger.info("Launching Camoufox browser for Cloudflare bypass")

        # Camoufox handles its own playwright initialization
        self.browser = await AsyncCamoufox(
            headless=self.config.playwright_headless
        ).start()

        self.context = await self.browser.new_context(
            viewport={
                "width": self.config.browser_viewport_width,
                "height": self.config.browser_viewport_height,
            }
        )

        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit: cleanup browser."""
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

    async def _verify_login_form_ready(self) -> None:
        if not self.page:
            raise RuntimeError("Page not initialized")

        try:
            await self.page.wait_for_selector(
                self.config.username_selector, state="visible", timeout=10000
            )
        except Exception as e:
            raise Exception(f"Username field not ready: {e}")

        try:
            await self.page.wait_for_selector(
                self.config.password_selector, state="visible", timeout=5000
            )
        except Exception as e:
            raise Exception(f"Password field not ready: {e}")

        try:
            await self.page.wait_for_selector(
                self.config.submit_selector, state="visible", timeout=3000
            )
        except Exception as e:
            raise Exception(f"Submit button not ready: {e}")

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

        try:
            response = await self.page.goto(
                self.config.login_url,
                wait_until="domcontentloaded",
                timeout=self.config.login_timeout * 1000,
            )

            current_url = self.page.url
            if response and (
                response.status == 403 or "cloudflare" in current_url.lower()
            ):
                logger.warning(f"Cloudflare challenge detected at {current_url}")
                await asyncio.sleep(5)

            await asyncio.sleep(random.uniform(1.0, 3.0))

            await self.page.mouse.wheel(0, random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await self.page.mouse.wheel(0, -random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.5, 1.0))

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
                logger.info(
                    f"Login attempt {attempt + 1}/{self.config.max_login_retries}"
                )

                # Fill username field with human-like delay
                for char in username:
                    await self.page.type(
                        self.config.username_selector,
                        char,
                        delay=random.randint(50, 150),
                    )

                await asyncio.sleep(random.uniform(0.5, 1.0))

                # Fill password field with human-like delay
                for char in password:
                    await self.page.type(
                        self.config.password_selector,
                        char,
                        delay=random.randint(50, 150),
                    )

                await asyncio.sleep(random.uniform(0.5, 1.0))

                # Move mouse to submit button before clicking
                submit_button = await self.page.query_selector(
                    self.config.submit_selector
                )
                if submit_button:
                    box = await submit_button.bounding_box()
                    if box:
                        await self.page.mouse.move(
                            box["x"] + box["width"] / 2 + random.randint(-5, 5),
                            box["y"] + box["height"] / 2 + random.randint(-5, 5),
                            steps=random.randint(5, 15),
                        )

                await asyncio.sleep(random.uniform(0.2, 0.5))
                await self.page.click(self.config.submit_selector)

                # Wait for navigation completion
                await self.page.wait_for_load_state(
                    "networkidle",
                    timeout=self.config.login_timeout * 1000,
                )

                # Verify login success by checking if login form is still visible
                try:
                    # Short timeout to check if we're still on login page
                    is_login_visible = await self.page.is_visible(
                        self.config.username_selector, timeout=2000
                    )
                    if is_login_visible:
                        logger.warning("Login form still visible after submission")
                        raise LoginError(
                            "Login failed - form still visible",
                            context={"url": self.page.url},
                        )
                except Exception as e:
                    # Ignore timeout or other errors checking visibility - assume success if navigation happened
                    if not isinstance(e, LoginError):
                        pass
                    else:
                        raise

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
