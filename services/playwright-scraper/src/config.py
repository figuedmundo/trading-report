"""
Environment configuration management.

Loads and validates environment variables from .env file.
Provides centralized access to all configuration values.
"""

import os
from typing import Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration from environment variables."""

    # Trading Portal Credentials
    trading_portal_username: Optional[str] = os.getenv("TRADING_PORTAL_USERNAME")
    trading_portal_password: Optional[str] = os.getenv("TRADING_PORTAL_PASSWORD")

    # Service Configuration
    service_port: int = int(os.getenv("SERVICE_PORT", "8002"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    playwright_headless: bool = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

    # Playwright Configuration
    browser_viewport_width: int = 1920
    browser_viewport_height: int = 1080
    browser_args: list = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--single-process",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-plugins",
    ]
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Timeouts (in seconds)
    page_load_timeout: int = 60
    login_timeout: int = 30
    request_timeout: int = 120
    image_download_timeout: int = 30

    # Login Configuration
    login_url: str = "https://protradingskills.com/wp-login.php"
    username_selector: str = 'input[id="user_login"]'
    password_selector: str = 'input[id="user_pass"]'
    submit_selector: str = 'input[id="wp-submit"]'
    max_login_retries: int = 3

    # Content Extraction
    title_selector: str = "article h2"
    content_container_selector: str = "div.entry-content"


def get_config() -> Config:
    """Get the current configuration instance."""
    return Config()


def validate_config() -> bool:
    """
    Validate that all required configuration is set.

    Returns True if valid, False otherwise.
    """
    config = get_config()

    required_fields = [
        ("TRADING_PORTAL_USERNAME", config.trading_portal_username),
        ("TRADING_PORTAL_PASSWORD", config.trading_portal_password),
    ]

    all_valid = True
    for field_name, field_value in required_fields:
        if not field_value:
            logger.warning(f"Configuration warning: {field_name} not properly set")
            all_valid = False

    return all_valid
