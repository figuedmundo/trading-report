"""
Environment configuration management.

Loads and validates environment variables from .env file.
Provides centralized access to all configuration values.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration from environment variables."""

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/trading_reports"
    )

    # Webhook security
    webhook_signature_secret: str = os.getenv(
        "WEBHOOK_SIGNATURE_SECRET",
        "your-secret-key-here"
    )
    api_key_fallback: Optional[str] = os.getenv("API_KEY_FALLBACK")

    # Report detection
    report_keywords: List[str] = [
        kw.strip() for kw in os.getenv(
            "REPORT_KEYWORDS",
            "trading report,analysis,recommendation,trade alert"
        ).split(",")
    ]

    # Portal configuration
    trusted_domains: List[str] = [
        domain.strip() for domain in os.getenv(
            "TRUSTED_DOMAINS",
            "protradingskills.com"
        ).split(",")
    ]

    # Rate limiting
    rate_limit_per_second: int = int(os.getenv("RATE_LIMIT_PER_SECOND", "1"))
    rate_limit_per_hour: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


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
        ("DATABASE_URL", config.database_url),
        ("WEBHOOK_SIGNATURE_SECRET", config.webhook_signature_secret),
    ]

    all_valid = True
    for field_name, field_value in required_fields:
        if not field_value or field_value.startswith("your-"):
            logger.warning(f"Configuration warning: {field_name} not properly set")
            all_valid = False

    return all_valid
