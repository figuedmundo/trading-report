"""
Environment configuration management for health monitoring service.

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

    # Database Configuration
    database_url: Optional[str] = os.getenv("DATABASE_URL")

    # Health Check Configuration
    health_check_interval: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
    health_check_timeout: int = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))
    enable_health_monitoring: bool = os.getenv("ENABLE_HEALTH_MONITORING", "true").lower() == "true"

    # Alert Configuration
    alert_email_admin: Optional[str] = os.getenv("ALERT_EMAIL_ADMIN", "admin@example.com")
    alert_batch_window: int = int(os.getenv("ALERT_BATCH_WINDOW", "60"))  # minutes
    alert_auto_resolve_window: int = int(os.getenv("ALERT_AUTO_RESOLVE_WINDOW", "5"))  # minutes
    notification_service_url: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8004")

    # Error Log Retention
    error_log_retention_days: int = int(os.getenv("ERROR_LOG_RETENTION_DAYS", "30"))
    health_check_retention_days: int = int(os.getenv("HEALTH_CHECK_RETENTION_DAYS", "7"))

    # Service URLs for health checks
    email_webhook_url: str = os.getenv("EMAIL_WEBHOOK_URL", "http://email-webhook:8001")
    playwright_scraper_url: str = os.getenv("PLAYWRIGHT_SCRAPER_URL", "http://playwright-scraper:8002")
    ai_analyzer_url: str = os.getenv("AI_ANALYZER_URL", "http://ai-analyzer:8000")
    notification_service_health_url: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8004")
    n8n_url: str = os.getenv("N8N_URL", "http://n8n:5678")


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
        ("ALERT_EMAIL_ADMIN", config.alert_email_admin),
    ]

    all_valid = True
    for field_name, field_value in required_fields:
        if not field_value:
            logger.warning(f"Configuration warning: {field_name} not properly set")
            all_valid = False

    return all_valid
