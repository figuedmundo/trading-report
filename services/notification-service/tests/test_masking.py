"""Tests for credential masking utility."""

from src.utils.masking import (
    mask_email,
    mask_chat_id,
    mask_phone,
    mask_api_token,
    mask_recipient,
)


def test_mask_email():
    """Test email masking."""
    assert mask_email("user@example.com") == "u***@example.com"
    assert mask_email("a@example.com") == "*@example.com"
    assert mask_email("") == "***"


def test_mask_chat_id():
    """Test Telegram chat ID masking."""
    assert mask_chat_id("123456789") == "123456****"
    assert mask_chat_id("12345") == "*****"
    assert mask_chat_id("") == "***"


def test_mask_phone():
    """Test phone number masking."""
    assert mask_phone("+1234567890") == "+123****"
    assert mask_phone("1234567890") == "123*******"
    assert mask_phone("") == "***"


def test_mask_api_token():
    """Test API token masking."""
    token = "secret-token-12345"
    masked = mask_api_token(token)
    assert masked.endswith("****")
    assert not masked.startswith("secret")


def test_mask_recipient_email():
    """Test recipient masking for email channel."""
    masked = mask_recipient("user@example.com", "email")
    assert "@" in masked
    assert "user" not in masked


def test_mask_recipient_telegram():
    """Test recipient masking for Telegram channel."""
    masked = mask_recipient("123456789", "telegram")
    assert "123456" in masked
    assert "789" not in masked


def test_mask_recipient_sms():
    """Test recipient masking for SMS channel."""
    masked = mask_recipient("+1234567890", "sms")
    assert "+123" in masked
    assert "7890" not in masked
