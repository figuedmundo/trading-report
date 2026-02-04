"""
Browser lifecycle management and authentication handling with Cloudflare bypass techniques.

Provides BrowserManager class for context manager pattern and enhanced login flow.
"""

import asyncio
import time
import random
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from playwright_stealth import stealth
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

    async def __aenter__(self) -> "BrowserManager":
        """
        Async context manager entry: launch browser.

        Returns:
            Self for use in with statement
        """
        logger.info("Launching browser with Cloudflare bypass techniques")

        try:
            self.playwright = await async_playwright().start()

            # Enhanced browser arguments for stealth
            browser_args = [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-blink-features=AutomationControlled",
                "--disable-ipc",
                "--exclude-switches",
                "--disable-password-manager",
                "--disable-default-apps",
                "--disable-translate-new-ux",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]

            self.browser = await self.playwright.chromium.launch(
                headless=self.config.playwright_headless,
                args=browser_args,
            )

            # Create browser context with anti-detection measures
            self.context = await self.browser.new_context(
                viewport={
                    "width": self.config.browser_viewport_width,
                    "height": self.config.browser_viewport_height,
                },
                user_agent=self.config.user_agent,
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Cache-Control": "max-age=0",
                },
            )

            self.page = await self.context.new_page()

            # Apply stealth to the page
            await stealth(self.page)

            return self

        except Exception as e:
            logger.error(f"Error setting up browser: {e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Async context manager exit: cleanup browser.

        Ensures browser always closes, even if errors occur.
        """
        logger.info("Cleaning up browser resources")

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

    async def _verify_login_form_ready(self) -> None:
        """
        Verify that login form elements are present and visible.
        """
        logger.info("Verifying login form readiness")

        try:
            # Wait for username field to be visible
            await self.page.wait_for_selector(
                self.config.username_selector, state="visible", timeout=10000
            )
            logger.info("Username field is visible")
        except Exception as e:
            logger.error(f"Username field verification failed: {e}")
            raise Exception(f"Username field not ready: {e}")

        try:
            # Wait for password field to be visible
            await self.page.wait_for_selector(
                self.config.password_selector, state="visible", timeout=5000
            )
            logger.info("Password field is visible")
        except Exception as e:
            logger.error(f"Password field verification failed: {e}")
            raise Exception(f"Password field not ready: {e}")

        try:
            # Wait for submit button to be visible
            await self.page.wait_for_selector(
                self.config.submit_selector, state="visible", timeout=3000
            )
            logger.info("Submit button is visible")
        except Exception as e:
            logger.error(f"Submit button verification failed: {e}")
            raise Exception(f"Submit button not ready: {e}")

        logger.info("Login form verification completed - all elements visible")

    async def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        """
        Perform login with enhanced anti-detection measures.
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

        logger.info(f"Starting login process with username: {username[:8]}...")

        # Navigate to login page with debugging
        try:
            response = await self.page.goto(
                self.config.login_url,
                wait_until="domcontentloaded",  # Basic page load
                timeout=self.config.login_timeout * 1000,
            )

            # Check if we got a valid response
            if response and response.status >= 400:
                raise LoginError(
                    f"Login page returned HTTP {response.status}",
                    context={"url": self.config.login_url, "status": response.status},
                )

            # Debug: Check current page state
            current_url = self.page.url
            page_title = await self.page.title()
            logger.info(f"Page loaded - URL: {current_url}, Title: {page_title}")

            # Check for Cloudflare challenges
            if "cloudflare" in current_url.lower() or response.status == 403:
                logger.warning("Cloudflare challenge detected")

                # Handle Turnstile CAPTCHA if present
                try:
                    # Look for Cloudflare Turnstile iframe
                    await self.page.wait_for_selector(
                        'iframe[src*="turnstile"]', timeout=5000
                    )

                    # Switch to iframe context
                    iframe_element = await self.page.query_selector(
                        'iframe[src*="turnstile"]'
                    )
                    if iframe_element:
                        iframe_content_frame = await iframe_element.content_frame()

                        # Look for Turnstile verification
                        await iframe_content_frame.wait_for_selector(
                            "[data-sitekey]", timeout=5000
                        )

                        # Extract sitekey for verification
                        sitekey = await iframe_content_frame.get_attribute(
                            "data-sitekey"
                        )

                        if sitekey:
                            logger.info(
                                f"Cloudflare Turnstile detected with sitekey: {sitekey}"
                            )

                            # Solve Turnstile challenge using browserless.io approach
                            solution = await self._solve_turnstile_challenge(
                                iframe_content_frame, sitekey
                            )

                            if solution:
                                logger.info(f"Turnstile challenge solved: {solution}")
                            else:
                                logger.warning("Turnstile challenge solution failed")
                    else:
                        logger.warning("Turnstile iframe not found")
                except Exception as e:
                    logger.warning(f"Error detecting Turnstile: {e}")

            # Additional wait for page to settle
            await asyncio.sleep(2)

        except Exception as e:
            raise LoginError(
                f"Failed to navigate to login page: {e}",
                context={"url": self.config.login_url},
            )

        # Verify login form is ready before attempting interaction
        await self._verify_login_form_ready()

        logger.info(
            f"Filling form with selectors: user={self.config.username_selector}, pass={self.config.password_selector}"
        )

        # Retry logic with exponential backoff
        backoff_delays = [1, 2, 4]  # seconds
        last_error = None

        for attempt in range(self.config.max_login_retries):
            try:
                logger.info(
                    f"Login attempt {attempt + 1}/{self.config.max_login_retries}"
                )

                # Fill username field
                await self.page.fill(self.config.username_selector, username)

                # Fill password field
                await self.page.fill(self.config.password_selector, password)

                # Submit form
                await self.page.click(self.config.submit_selector)

                # Wait for navigation and verify success
                await self.page.wait_for_load_state(
                    "networkidle", timeout=self.config.login_timeout * 1000
                )

                # Simple success check - if we're not on login page anymore, we're logged in
                current_url = self.page.url
                if "wp-login.php" not in current_url:
                    logger.info(f"Login successful - redirected to: {current_url}")
                    return True
                else:
                    # Look for error messages
                    try:
                        error_element = await self.page.query_selector(
                            ".login .message, .error"
                        )
                        if error_element:
                            error_text = await error_element.text_content()
                            logger.warning(f"Login failed with error: {error_text}")
                        else:
                            logger.warning("Login failed - no error message visible")
                    except Exception:
                        logger.warning(
                            "Login failed - could not check for error message"
                        )

            except LoginError:
                raise
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

    async def _solve_turnstile_challenge(
        self, iframe_content_frame, sitekey: str
    ) -> Optional[str]:
        """
        Solve Cloudflare Turnstile challenge using browserless.io approach.

        Args:
            iframe_content_frame: The iframe context containing Turnstile
            sitekey: The sitekey for verification

        Returns:
            Solution token if successful, None otherwise
        """
        try:
            logger.info(
                f"Attempting to solve Turnstile challenge with sitekey: {sitekey}"
            )

            # Wait for Turnstile to load
            await iframe_content_frame.wait_for_load_state(
                "domcontentloaded", timeout=10000
            )

            # Use browserless.io-like approach for Turnstile solving
            # This is a complex challenge that would require browserless.io or similar service
            # For now, we'll acknowledge the challenge and try to continue
            logger.warning("Turnstile challenge detected - requires advanced solving")

            # Return None to indicate challenge could not be solved automatically
            return None

        except Exception as e:
            logger.error(f"Turnstile challenge solving failed: {e}")
            return None
