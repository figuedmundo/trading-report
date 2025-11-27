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

    # AI Provider Configuration
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")

    # Service Configuration
    service_port: int = int(os.getenv("SERVICE_PORT", "8002"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    analysis_timeout: int = int(os.getenv("ANALYSIS_TIMEOUT", "30"))

    # Database Configuration
    database_url: Optional[str] = os.getenv("DATABASE_URL")


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
        ("ANTHROPIC_API_KEY or GROQ_API_KEY", config.anthropic_api_key or config.groq_api_key),
        ("DATABASE_URL", config.database_url),
    ]

    all_valid = True
    for field_name, field_value in required_fields:
        if not field_value:
            logger.warning(f"Configuration warning: {field_name} not properly set")
            all_valid = False

    # Check if at least one API key is configured
    if not (config.anthropic_api_key or config.groq_api_key):
        logger.error("Configuration error: At least one API key (ANTHROPIC_API_KEY or GROQ_API_KEY) must be set")
        all_valid = False

    return all_valid
