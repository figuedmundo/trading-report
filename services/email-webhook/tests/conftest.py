"""Shared test fixtures and configuration for email-webhook service tests."""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_env(monkeypatch):
    """Fixture to set up common test environment variables."""
    # Set required environment variables for tests
    monkeypatch.setenv("WEBHOOK_SECRET_KEY", "test_secret_key_" + "a" * 17)
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("RATE_LIMIT_PER_IP_MINUTE", "5")
    monkeypatch.setenv("RATE_LIMIT_PER_IP_HOUR", "50")
    monkeypatch.setenv("RATE_LIMIT_GLOBAL_HOUR", "100")
    monkeypatch.setenv("RATE_LIMIT_BAN_THRESHOLD", "10")
    monkeypatch.setenv("RATE_LIMIT_BAN_DURATION_HOURS", "1")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


@pytest.fixture
def mock_db_pool():
    """Fixture to provide a mock database pool."""
    pool = AsyncMock()
    return pool


@pytest.fixture
def mock_db_connection():
    """Fixture to provide a mock database connection."""
    conn = AsyncMock()
    return conn
