"""
Configuration management for credential service.

Loads and validates configuration from environment variables.
"""

import os
from typing import Optional
from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    """Configuration model with validation."""

    model_config = ConfigDict(case_sensitive=False)

    database_url: str
    credential_encryption_key: str
    service_port: int = 8002
    log_level: str = 'INFO'


def get_config() -> Config:
    """
    Load and validate configuration from environment variables.

    Required environment variables:
        - DATABASE_URL: PostgreSQL connection string
        - CREDENTIAL_ENCRYPTION_KEY: Base64-encoded 32-byte Fernet key

    Optional environment variables:
        - CREDENTIAL_SERVICE_PORT: Service port (default: 8002)
        - LOG_LEVEL: Logging level (default: INFO)

    Returns:
        Config: Validated configuration object

    Raises:
        ValueError: If required environment variables are missing or invalid
    """
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError('DATABASE_URL environment variable is required')

    encryption_key = os.environ.get('CREDENTIAL_ENCRYPTION_KEY')
    if not encryption_key:
        raise ValueError('CREDENTIAL_ENCRYPTION_KEY environment variable is required')

    service_port = int(os.environ.get('CREDENTIAL_SERVICE_PORT', '8002'))
    log_level = os.environ.get('LOG_LEVEL', 'INFO')

    return Config(
        database_url=database_url,
        credential_encryption_key=encryption_key,
        service_port=service_port,
        log_level=log_level,
    )
