"""Tests for configuration validation and loading.

Tests cover:
- WEBHOOK_SECRET_KEY minimum length validation (32 chars)
- CIDR IP range parsing from environment variables
- Database connection validation at startup
"""

import pytest
import os
from src.config import Config, get_config, validate_config, parse_ip_ranges
from src.utils.exceptions import DatabaseError


class TestConfigLoading:
    """Tests for basic configuration loading."""

    def test_default_values_are_applied(self):
        """Test that default values are applied when environment variables are not set."""
        # These should have defaults
        config = get_config()
        assert config.rate_limit_per_ip_minute == 5
        assert config.rate_limit_per_ip_hour == 50
        assert config.rate_limit_global_hour == 100
        assert config.service_port == 8001
        assert config.log_level == "INFO"

    def test_environment_variables_override_defaults(self, monkeypatch):
        """Test that environment variables override default values."""
        monkeypatch.setenv("RATE_LIMIT_PER_IP_MINUTE", "10")
        monkeypatch.setenv("SERVICE_PORT", "9000")
        
        # Need to reload the config
        config = Config()
        assert config.rate_limit_per_ip_minute == 10
        assert config.service_port == 9000

    def test_boolean_environment_variables(self, monkeypatch):
        """Test that boolean configuration values are parsed correctly."""
        monkeypatch.setenv("SIGNATURE_VALIDATION_ENABLED", "false")
        monkeypatch.setenv("SECURITY_ALERT_TELEGRAM", "false")
        
        config = Config()
        assert config.signature_validation_enabled is False
        assert config.security_alert_telegram is False

    def test_boolean_defaults_to_true(self, monkeypatch):
        """Test that boolean values default to True."""
        monkeypatch.delenv("SIGNATURE_VALIDATION_ENABLED", raising=False)
        monkeypatch.delenv("SECURITY_ALERT_TELEGRAM", raising=False)
        
        config = Config()
        assert config.signature_validation_enabled is True
        assert config.security_alert_telegram is True


class TestWebhookSecretKeyValidation:
    """Tests for WEBHOOK_SECRET_KEY validation."""

    def test_webhook_secret_key_minimum_length_validation(self, monkeypatch):
        """Test that WEBHOOK_SECRET_KEY must be at least 32 characters."""
        # Set a short key
        monkeypatch.setenv("WEBHOOK_SECRET_KEY", "short_key_123")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:pass@localhost/test")
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_config()

    def test_webhook_secret_key_exactly_32_characters_valid(self, monkeypatch):
        """Test that WEBHOOK_SECRET_KEY with exactly 32 characters is valid."""
        secret_key = "a" * 32  # Exactly 32 characters
        monkeypatch.setenv("WEBHOOK_SECRET_KEY", secret_key)
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:pass@localhost/test")
        
        # Should not raise
        config = Config()
        assert len(config.webhook_secret_key) == 32
        assert validate_config() is True

    def test_webhook_secret_key_more_than_32_characters_valid(self, monkeypatch):
        """Test that WEBHOOK_SECRET_KEY with more than 32 characters is valid."""
        secret_key = "a" * 64  # 64 characters
        monkeypatch.setenv("WEBHOOK_SECRET_KEY", secret_key)
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:pass@localhost/test")
        
        # Should not raise
        config = Config()
        assert len(config.webhook_secret_key) == 64
        assert validate_config() is True

    def test_webhook_secret_key_required(self, monkeypatch):
        """Test that WEBHOOK_SECRET_KEY is required."""
        monkeypatch.delenv("WEBHOOK_SECRET_KEY", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:pass@localhost/test")
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_config()


class TestIPRangesParsing:
    """Tests for CIDR IP range parsing."""

    def test_parse_single_cidr_range(self, monkeypatch):
        """Test parsing a single CIDR range."""
        monkeypatch.setenv("MAILGUN_IP_RANGES", "192.168.1.0/24")
        config = Config()
        ranges = parse_ip_ranges(config.mailgun_ip_ranges)
        
        assert len(ranges) == 1
        assert ranges[0] == "192.168.1.0/24"

    def test_parse_multiple_cidr_ranges(self, monkeypatch):
        """Test parsing multiple comma-separated CIDR ranges."""
        monkeypatch.setenv("MAILGUN_IP_RANGES", "192.168.1.0/24,10.0.0.0/8,172.16.0.0/12")
        config = Config()
        ranges = parse_ip_ranges(config.mailgun_ip_ranges)
        
        assert len(ranges) == 3
        assert "192.168.1.0/24" in ranges
        assert "10.0.0.0/8" in ranges
        assert "172.16.0.0/12" in ranges

    def test_parse_cidr_ranges_with_whitespace(self, monkeypatch):
        """Test that whitespace is trimmed from CIDR ranges."""
        monkeypatch.setenv("SENDGRID_IP_RANGES", " 192.168.1.0/24 , 10.0.0.0/8 ")
        config = Config()
        ranges = parse_ip_ranges(config.sendgrid_ip_ranges)
        
        assert len(ranges) == 2
        assert ranges[0] == "192.168.1.0/24"
        assert ranges[1] == "10.0.0.0/8"

    def test_parse_empty_cidr_ranges(self, monkeypatch):
        """Test parsing empty CIDR ranges returns empty list."""
        monkeypatch.setenv("CUSTOM_ALLOWED_IPS", "")
        config = Config()
        ranges = parse_ip_ranges(config.custom_allowed_ips)
        
        assert len(ranges) == 0
        assert ranges == []

    def test_parse_none_cidr_ranges(self):
        """Test parsing None CIDR ranges returns empty list."""
        ranges = parse_ip_ranges(None)
        assert len(ranges) == 0

    def test_parse_large_mailgun_sendgrid_ranges(self, monkeypatch):
        """Test parsing realistic Mailgun and SendGrid IP ranges."""
        # Realistic Mailgun and SendGrid CIDR blocks
        monkeypatch.setenv("MAILGUN_IP_RANGES", "149.72.0.0/16,161.38.0.0/16")
        monkeypatch.setenv("SENDGRID_IP_RANGES", "168.245.0.0/16,167.89.0.0/16")
        
        config = Config()
        mailgun_ranges = parse_ip_ranges(config.mailgun_ip_ranges)
        sendgrid_ranges = parse_ip_ranges(config.sendgrid_ip_ranges)
        
        assert len(mailgun_ranges) == 2
        assert len(sendgrid_ranges) == 2
        assert "149.72.0.0/16" in mailgun_ranges
        assert "168.245.0.0/16" in sendgrid_ranges


class TestDatabaseConfiguration:
    """Tests for database connection validation."""

    def test_database_url_required(self, monkeypatch):
        """Test that DATABASE_URL is required."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("WEBHOOK_SECRET_KEY", "a" * 32)
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_config()

    def test_database_url_loaded_from_environment(self, monkeypatch):
        """Test that DATABASE_URL is loaded from environment."""
        test_url = "postgresql://user:pass@localhost:5432/db"
        monkeypatch.setenv("DATABASE_URL", test_url)
        monkeypatch.setenv("WEBHOOK_SECRET_KEY", "a" * 32)
        
        config = Config()
        assert config.database_url == test_url


class TestRateLimitValidation:
    """Tests for rate limit configuration validation."""

    def test_rate_limit_values_must_be_positive(self, monkeypatch):
        """Test that rate limit values must be positive integers."""
        monkeypatch.setenv("RATE_LIMIT_PER_IP_MINUTE", "0")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:pass@localhost/test")
        monkeypatch.setenv("WEBHOOK_SECRET_KEY", "a" * 32)
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_config()

    def test_rate_limit_negative_values_rejected(self, monkeypatch):
        """Test that negative rate limit values are rejected."""
        monkeypatch.setenv("RATE_LIMIT_PER_IP_HOUR", "-50")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:pass@localhost/test")
        monkeypatch.setenv("WEBHOOK_SECRET_KEY", "a" * 32)
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_config()

    def test_all_rate_limits_must_be_positive(self, monkeypatch):
        """Test that all rate limit configurations must be positive."""
        monkeypatch.setenv("WEBHOOK_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:pass@localhost/test")
        monkeypatch.setenv("RATE_LIMIT_PER_IP_MINUTE", "5")
        monkeypatch.setenv("RATE_LIMIT_PER_IP_HOUR", "50")
        monkeypatch.setenv("RATE_LIMIT_GLOBAL_HOUR", "0")  # Invalid: 0
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_config()


class TestConfigurationErrorHandling:
    """Tests for configuration error handling."""

    def test_multiple_configuration_errors_all_reported(self, monkeypatch):
        """Test that all configuration errors are caught."""
        monkeypatch.delenv("WEBHOOK_SECRET_KEY", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_config()

    def test_validate_config_returns_true_on_success(self, monkeypatch):
        """Test that validate_config returns True when all validations pass."""
        monkeypatch.setenv("WEBHOOK_SECRET_KEY", "valid_key_" + "a" * 23)
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:pass@localhost/test")
        monkeypatch.setenv("RATE_LIMIT_PER_IP_MINUTE", "5")
        monkeypatch.setenv("RATE_LIMIT_PER_IP_HOUR", "50")
        monkeypatch.setenv("RATE_LIMIT_GLOBAL_HOUR", "100")
        monkeypatch.setenv("RATE_LIMIT_BAN_THRESHOLD", "10")
        monkeypatch.setenv("RATE_LIMIT_BAN_DURATION_HOURS", "1")
        
        # Should return True without raising
        result = validate_config()
        assert result is True
