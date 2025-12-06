"""Configuration management for Gmail Bridge service."""

import os
from typing import Optional


class Config:
    """Gmail Bridge service configuration from environment variables."""

    # Service
    SERVICE_NAME = "gmail-bridge"
    SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8005"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # IMAP Configuration
    IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))

    # Gmail Credentials
    SMTP_USER = os.getenv("SMTP_USER")  # Gmail email address
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Gmail app password

    # Webhook Configuration
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:5678/webhook/trading-reports")
    WEBHOOK_SECRET_KEY = os.getenv("WEBHOOK_SECRET_KEY")  # Shared secret for signature
    WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "30"))  # seconds

    # Polling Configuration
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))  # seconds
    EMAIL_SEARCH_CRITERIA = os.getenv("EMAIL_SEARCH_CRITERIA", "UNSEEN")
    EMAIL_SENDER_FILTER = os.getenv("EMAIL_SENDER_FILTER", "")  # Optional

    # Email Processing
    MARK_AS_READ = os.getenv("MARK_AS_READ", "false").lower() == "true"

    # Database Configuration (for audit trail)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Service URLs (for health checks)
    N8N_URL = os.getenv("N8N_URL", "http://n8n:5678")

    @classmethod
    def validate(cls) -> None:
        """Validate configuration and log warnings for missing critical settings."""
        import logging
        logger = logging.getLogger(__name__)

        if not cls.SMTP_USER:
            logger.warning("SMTP_USER not set - Gmail polling will not work until configured")
        if not cls.EMAIL_PASSWORD:
            logger.warning("EMAIL_PASSWORD not set - Gmail polling will not work until configured")
        if not cls.WEBHOOK_URL:
            logger.warning("WEBHOOK_URL not set - emails will not be forwarded")
        if not cls.WEBHOOK_SECRET_KEY:
            logger.warning("WEBHOOK_SECRET_KEY not set - webhook requests will lack signature and fail")
