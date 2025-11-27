"""Tests for configuration module."""

import os
import pytest
from src.config import Config, validate_config


def test_config_loads_environment_variables(monkeypatch):
    """Test that Config loads environment variables."""
    monkeypatch.setenv("SERVICE_PORT", "9999")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test@localhost/db")

    config = Config()

    assert config.service_port == 9999
    assert config.log_level == "DEBUG"
    assert config.database_url == "postgresql://test@localhost/db"


def test_config_smtp_settings(monkeypatch):
    """Test SMTP configuration loading."""
    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USER", "user@test.com")
    monkeypatch.setenv("SMTP_PASSWORD", "password123")
    monkeypatch.setenv("SENDER_EMAIL", "sender@test.com")

    config = Config()

    assert config.smtp_host == "smtp.test.com"
    assert config.smtp_port == 465
    assert config.smtp_user == "user@test.com"
    assert config.smtp_password == "password123"
    assert config.sender_email == "sender@test.com"


def test_config_defaults(monkeypatch):
    """Test that Config uses sensible defaults."""
    # Clear env vars
    monkeypatch.delenv("SERVICE_PORT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    config = Config()

    assert config.service_port == 8003
    assert config.log_level == "INFO"


def test_validate_config_requires_database_url(monkeypatch):
    """Test that validate_config requires DATABASE_URL."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    result = validate_config()

    assert result is False


def test_validate_config_succeeds_with_database_url(monkeypatch):
    """Test that validate_config passes with DATABASE_URL."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test@localhost/db")

    result = validate_config()

    assert result is True
