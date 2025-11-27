"""Tests for channel implementations."""

import pytest
from src.channels.email import EmailChannel
from src.channels.telegram import TelegramChannel


class TestEmailChannel:
    """Tests for EmailChannel."""

    def test_validate_recipient_valid_email(self):
        """Test email validation with valid email."""
        channel = EmailChannel("email", {})
        assert channel.validate_recipient("user@example.com") is True

    def test_validate_recipient_invalid_email(self):
        """Test email validation with invalid email."""
        channel = EmailChannel("email", {})
        assert channel.validate_recipient("invalid-email") is False

    def test_validate_recipient_edge_cases(self):
        """Test email validation edge cases."""
        channel = EmailChannel("email", {})
        assert channel.validate_recipient("user+tag@example.co.uk") is True
        assert channel.validate_recipient("@example.com") is False
        assert channel.validate_recipient("user@") is False

    def test_validate_config_requires_smtp_settings(self):
        """Test SMTP configuration validation."""
        channel = EmailChannel("email", {})
        assert channel.validate_config() is False

        channel = EmailChannel("email", {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@test.com",
            "SMTP_PASSWORD": "password",
        })
        assert channel.validate_config() is True


class TestTelegramChannel:
    """Tests for TelegramChannel."""

    def test_validate_recipient_valid_chat_id(self):
        """Test Telegram chat ID validation with valid ID."""
        channel = TelegramChannel("telegram", {})
        assert channel.validate_recipient("123456789") is True

    def test_validate_recipient_invalid_chat_id(self):
        """Test Telegram chat ID validation with invalid ID."""
        channel = TelegramChannel("telegram", {})
        assert channel.validate_recipient("abc-def") is False

    def test_validate_config_requires_bot_token(self):
        """Test Telegram bot token validation."""
        channel = TelegramChannel("telegram", {})
        assert channel.validate_config() is False

        channel = TelegramChannel("telegram", {
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF",
        })
        assert channel.validate_config() is True

    def test_split_message_under_limit(self):
        """Test message splitting for messages under limit."""
        channel = TelegramChannel("telegram", {})
        message = "Short message"
        chunks = channel._split_message(message, 4096)
        assert len(chunks) == 1
        assert chunks[0] == message

    def test_split_message_over_limit(self):
        """Test message splitting for messages over limit."""
        channel = TelegramChannel("telegram", {})
        message = "a" * 5000
        chunks = channel._split_message(message, 1000)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 1000

    def test_split_message_respects_boundaries(self):
        """Test that message splitting respects word boundaries."""
        channel = TelegramChannel("telegram", {})
        message = "This is a test\n\nSecond paragraph\n\nThird paragraph"
        chunks = channel._split_message(message, 100)
        # Should split on double newline boundaries
        assert all("\n\n" not in chunk for chunk in chunks)
