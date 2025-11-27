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

    # Service Configuration
    service_port: int = int(os.getenv("SERVICE_PORT", "8003"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    service_name: str = os.getenv("SERVICE_NAME", "notification-service")

    # Database Configuration
    database_url: Optional[str] = os.getenv("DATABASE_URL")
    database_pool_min: int = int(os.getenv("DATABASE_POOL_MIN", "2"))
    database_pool_max: int = int(os.getenv("DATABASE_POOL_MAX", "10"))

    # SMTP Configuration (Email)
    smtp_host: Optional[str] = os.getenv("SMTP_HOST")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: Optional[str] = os.getenv("SMTP_USER")
    smtp_password: Optional[str] = os.getenv("SMTP_PASSWORD")
    sender_email: Optional[str] = os.getenv("SENDER_EMAIL")

    # Telegram Configuration
    telegram_bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")

    # Optional Configuration
    correlation_id_header: str = os.getenv("CORRELATION_ID_HEADER", "X-Correlation-ID")


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
    ]

    all_valid = True
    for field_name, field_value in required_fields:
        if not field_value:
            logger.warning(f"Configuration warning: {field_name} not properly set")
            all_valid = False

    # Check SMTP configuration if email channel enabled
    if config.smtp_host:
        smtp_required = [
            ("SMTP_USER", config.smtp_user),
            ("SMTP_PASSWORD", config.smtp_password),
            ("SENDER_EMAIL", config.sender_email),
        ]
        for field_name, field_value in smtp_required:
            if not field_value:
                logger.warning(f"Configuration warning: {field_name} not set (email channel may not work)")
                all_valid = False

    return all_valid
