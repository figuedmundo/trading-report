"""Environment configuration management for email-webhook service.

Loads and validates environment variables from .env file.
Provides centralized access to all security and rate limit configuration values.
"""

import os
from typing import Optional, List
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration from environment variables."""

    def __init__(self):
        """Initialize configuration by loading environment variables."""
        # Security Configuration
        self.webhook_secret_key: Optional[str] = os.getenv("WEBHOOK_SECRET_KEY")
        self.signature_validation_enabled: bool = os.getenv("SIGNATURE_VALIDATION_ENABLED", "true").lower() == "true"

        # IP Allowlist Configuration
        self.mailgun_ip_ranges: str = os.getenv("MAILGUN_IP_RANGES", "")
        self.sendgrid_ip_ranges: str = os.getenv("SENDGRID_IP_RANGES", "")
        self.custom_allowed_ips: str = os.getenv("CUSTOM_ALLOWED_IPS", "")
        self.ip_allowlist_cache_refresh_seconds: int = int(os.getenv("IP_ALLOWLIST_CACHE_REFRESH_SECONDS", "300"))

        # Rate Limiting Configuration
        self.rate_limit_per_ip_minute: int = int(os.getenv("RATE_LIMIT_PER_IP_MINUTE", "5"))
        self.rate_limit_per_ip_hour: int = int(os.getenv("RATE_LIMIT_PER_IP_HOUR", "50"))
        self.rate_limit_global_hour: int = int(os.getenv("RATE_LIMIT_GLOBAL_HOUR", "100"))
        self.rate_limit_ban_threshold: int = int(os.getenv("RATE_LIMIT_BAN_THRESHOLD", "10"))
        self.rate_limit_ban_duration_hours: int = int(os.getenv("RATE_LIMIT_BAN_DURATION_HOURS", "1"))
        self.rate_limit_authenticated_multiplier: int = int(os.getenv("RATE_LIMIT_AUTHENTICATED_MULTIPLIER", "5"))

        # Security Alerts Configuration
        self.security_alert_threshold: int = int(os.getenv("SECURITY_ALERT_THRESHOLD", "50"))
        self.security_alert_telegram: bool = os.getenv("SECURITY_ALERT_TELEGRAM", "true").lower() == "true"
        self.security_alert_debounce_minutes: int = int(os.getenv("SECURITY_ALERT_DEBOUNCE_MINUTES", "10"))

        # Service Configuration
        self.service_port: int = int(os.getenv("SERVICE_PORT", "8001"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.webhook_security_enabled: bool = os.getenv("WEBHOOK_SECURITY_ENABLED", "true").lower() == "true"

        # Database Configuration
        self.database_url: Optional[str] = os.getenv("DATABASE_URL")
        self.security_event_retention_days: int = int(os.getenv("SECURITY_EVENT_RETENTION_DAYS", "90"))


def get_config() -> Config:
    """Get the current configuration instance."""
    return Config()


def validate_config() -> bool:
    """Validate that all required configuration is set.

    Returns True if valid, raises ValueError otherwise.
    """
    config = get_config()

    # Check required fields
    required_fields = [
        ("WEBHOOK_SECRET_KEY", config.webhook_secret_key),
        ("DATABASE_URL", config.database_url),
    ]

    all_valid = True
    for field_name, field_value in required_fields:
        if not field_value:
            logger.error(f"Configuration error: {field_name} is not set")
            all_valid = False

    # Validate WEBHOOK_SECRET_KEY minimum length (32 characters)
    if config.webhook_secret_key and len(config.webhook_secret_key) < 32:
        logger.error(f"Configuration error: WEBHOOK_SECRET_KEY must be at least 32 characters long")
        all_valid = False

    # Validate positive integers for rate limiting
    rate_limit_configs = [
        ("RATE_LIMIT_PER_IP_MINUTE", config.rate_limit_per_ip_minute),
        ("RATE_LIMIT_PER_IP_HOUR", config.rate_limit_per_ip_hour),
        ("RATE_LIMIT_GLOBAL_HOUR", config.rate_limit_global_hour),
        ("RATE_LIMIT_BAN_THRESHOLD", config.rate_limit_ban_threshold),
        ("RATE_LIMIT_BAN_DURATION_HOURS", config.rate_limit_ban_duration_hours),
    ]

    for field_name, field_value in rate_limit_configs:
        if field_value <= 0:
            logger.error(f"Configuration error: {field_name} must be a positive integer")
            all_valid = False

    if not all_valid:
        raise ValueError("Configuration validation failed. Check logs for details.")

    return all_valid


def parse_ip_ranges(ranges_str: str) -> List[str]:
    """Parse comma-separated IP ranges from environment variable.

    Args:
        ranges_str: Comma-separated CIDR ranges (e.g., "192.168.1.0/24,10.0.0.0/8")

    Returns:
        List of CIDR ranges
    """
    if not ranges_str:
        return []

    return [ip.strip() for ip in ranges_str.split(",") if ip.strip()]
