"""Tests for signature validation components.

Tests for:
- Mailgun signature validator (timestamp + token + HMAC)
- SendGrid signature validator (ECDSA)
- Generic HMAC-SHA256 validator
- Auto-detection from request headers
"""

import pytest
import hmac
import hashlib
import time
import base64
from unittest.mock import patch, MagicMock
from src.security.validators import mailgun_validator
from src.security.validators import sendgrid_validator
from src.security.validators import generic_hmac_validator
from src.security import signature_validator
from src.utils.exceptions import SignatureValidationError


# Test fixtures
@pytest.fixture
def webhook_secret_key():
    """Generate a test webhook secret key."""
    return "test_secret_key_32_characters_long_for_testing_purposes_1234567890"


@pytest.fixture
def mock_config(webhook_secret_key):
    """Mock configuration with test secret key."""
    config = MagicMock()
    config.webhook_secret_key = webhook_secret_key
    config.signature_validation_enabled = True
    return config


@pytest.fixture
def sample_body():
    """Sample request body for testing."""
    return b'{"event": "message_clicked", "timestamp": 1234567890}'


# ============================================================================
# Mailgun Signature Validator Tests
# ============================================================================

class TestMailgunValidator:
    """Tests for Mailgun-specific signature validation."""

    def test_mailgun_valid_signature(self, mock_config, sample_body):
        """Test valid Mailgun signature verification."""
        with patch("src.security.validators.mailgun_validator.get_config", return_value=mock_config):
            timestamp = str(int(time.time()))
            token = "test_token_abc123"

            # Create valid signature
            message = timestamp + token
            expected_signature = hmac.new(
                mock_config.webhook_secret_key.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            headers = {
                "x-mailgun-signature": f"timestamp={timestamp} token={token} signature={expected_signature}"
            }

            # Should not raise exception
            result = mailgun_validator.validate(headers, sample_body)
            assert result is True

    def test_mailgun_invalid_signature(self, mock_config, sample_body):
        """Test invalid Mailgun signature verification."""
        with patch("src.security.validators.mailgun_validator.get_config", return_value=mock_config):
            timestamp = str(int(time.time()))
            token = "test_token_abc123"
            invalid_signature = "invalid_signature_here"

            headers = {
                "x-mailgun-signature": f"timestamp={timestamp} token={token} signature={invalid_signature}"
            }

            with pytest.raises(SignatureValidationError) as exc_info:
                mailgun_validator.validate(headers, sample_body)

            assert exc_info.value.error_code == "INVALID_SIGNATURE"

    def test_mailgun_missing_signature_header(self, mock_config, sample_body):
        """Test missing X-Mailgun-Signature header."""
        with patch("src.security.validators.mailgun_validator.get_config", return_value=mock_config):
            headers = {}

            with pytest.raises(SignatureValidationError) as exc_info:
                mailgun_validator.validate(headers, sample_body)

            assert "missing" in exc_info.value.context.get("reason", "").lower()

    def test_mailgun_invalid_header_format(self, mock_config, sample_body):
        """Test invalid X-Mailgun-Signature header format."""
        with patch("src.security.validators.mailgun_validator.get_config", return_value=mock_config):
            headers = {
                "x-mailgun-signature": "invalid_format_without_proper_parts"
            }

            with pytest.raises(SignatureValidationError) as exc_info:
                mailgun_validator.validate(headers, sample_body)

            assert "format" in exc_info.value.context.get("reason", "").lower() or \
                   "parse_error" in exc_info.value.context.get("reason", "")

    def test_mailgun_stale_timestamp(self, mock_config, sample_body):
        """Test rejection of old timestamps (>5 minutes)."""
        with patch("src.security.validators.mailgun_validator.get_config", return_value=mock_config):
            # Create timestamp from 10 minutes ago
            timestamp = str(int(time.time()) - 600)
            token = "test_token_abc123"

            message = timestamp + token
            expected_signature = hmac.new(
                mock_config.webhook_secret_key.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            headers = {
                "x-mailgun-signature": f"timestamp={timestamp} token={token} signature={expected_signature}"
            }

            with pytest.raises(SignatureValidationError) as exc_info:
                mailgun_validator.validate(headers, sample_body)

            assert "stale" in exc_info.value.context.get("reason", "").lower()

    def test_mailgun_future_timestamp(self, mock_config, sample_body):
        """Test rejection of future timestamps (>1 minute in future)."""
        with patch("src.security.validators.mailgun_validator.get_config", return_value=mock_config):
            # Create timestamp from 2 minutes in the future
            timestamp = str(int(time.time()) + 120)
            token = "test_token_abc123"

            message = timestamp + token
            expected_signature = hmac.new(
                mock_config.webhook_secret_key.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            headers = {
                "x-mailgun-signature": f"timestamp={timestamp} token={token} signature={expected_signature}"
            }

            with pytest.raises(SignatureValidationError) as exc_info:
                mailgun_validator.validate(headers, sample_body)

            assert "stale" in exc_info.value.context.get("reason", "").lower() or \
                   "future" in exc_info.value.context.get("reason", "").lower()


# ============================================================================
# SendGrid Signature Validator Tests
# ============================================================================

class TestSendGridValidator:
    """Tests for SendGrid ECDSA signature validation."""

    def test_sendgrid_missing_signature_header_falls_back_to_hmac(self, mock_config, sample_body):
        """Test that missing X-SendGrid-Signature falls back to generic HMAC."""
        with patch("src.security.validators.sendgrid_validator.get_config", return_value=mock_config):
            with patch("src.security.validators.sendgrid_validator.validate_generic_hmac") as mock_generic:
                mock_generic.return_value = True

                headers = {
                    "x-signature": hmac.new(
                        mock_config.webhook_secret_key.encode("utf-8"),
                        sample_body,
                        hashlib.sha256
                    ).hexdigest()
                }

                result = sendgrid_validator.validate(headers, sample_body)
                assert result is True
                mock_generic.assert_called_once()

    def test_sendgrid_missing_timestamp_falls_back_to_hmac(self, mock_config, sample_body):
        """Test that missing X-SendGrid-Timestamp falls back to generic HMAC."""
        with patch("src.security.validators.sendgrid_validator.get_config", return_value=mock_config):
            with patch("src.security.validators.sendgrid_validator.validate_generic_hmac") as mock_generic:
                mock_generic.return_value = True

                headers = {
                    "x-sendgrid-signature": "some_signature",
                    # No X-SendGrid-Timestamp header
                }

                result = sendgrid_validator.validate(headers, sample_body)
                assert result is True
                mock_generic.assert_called_once()

    def test_sendgrid_invalid_signature_falls_back_to_hmac(self, mock_config, sample_body):
        """Test that invalid ECDSA signature falls back to generic HMAC."""
        with patch("src.security.validators.sendgrid_validator.get_config", return_value=mock_config):
            with patch("src.security.validators.sendgrid_validator.validate_generic_hmac") as mock_generic:
                mock_generic.return_value = True

                # Create invalid base64 signature
                invalid_sig = base64.b64encode(b"invalid_signature").decode()

                headers = {
                    "x-sendgrid-signature": invalid_sig,
                    "x-sendgrid-timestamp": str(int(time.time())),
                }

                result = sendgrid_validator.validate(headers, sample_body)
                assert result is True
                mock_generic.assert_called_once()


# ============================================================================
# Generic HMAC Validator Tests
# ============================================================================

class TestGenericHMACValidator:
    """Tests for generic HMAC-SHA256 signature validation."""

    def test_generic_hmac_valid_signature_x_signature_header(self, mock_config, sample_body):
        """Test valid generic HMAC signature in X-Signature header."""
        with patch("src.security.validators.generic_hmac_validator.get_config", return_value=mock_config):
            # Create valid signature
            expected_signature = hmac.new(
                mock_config.webhook_secret_key.encode("utf-8"),
                sample_body,
                hashlib.sha256
            ).hexdigest()

            headers = {
                "x-signature": expected_signature
            }

            result = generic_hmac_validator.validate(headers, sample_body)
            assert result is True

    def test_generic_hmac_valid_signature_authorization_header(self, mock_config, sample_body):
        """Test valid generic HMAC signature in Authorization header."""
        with patch("src.security.validators.generic_hmac_validator.get_config", return_value=mock_config):
            # Create valid signature
            expected_signature = hmac.new(
                mock_config.webhook_secret_key.encode("utf-8"),
                sample_body,
                hashlib.sha256
            ).hexdigest()

            headers = {
                "authorization": f"Bearer {expected_signature}"
            }

            result = generic_hmac_validator.validate(headers, sample_body)
            assert result is True

    def test_generic_hmac_invalid_signature(self, mock_config, sample_body):
        """Test invalid generic HMAC signature."""
        with patch("src.security.validators.generic_hmac_validator.get_config", return_value=mock_config):
            headers = {
                "x-signature": "invalid_signature_here"
            }

            with pytest.raises(SignatureValidationError) as exc_info:
                generic_hmac_validator.validate(headers, sample_body)

            assert exc_info.value.error_code == "INVALID_SIGNATURE"

    def test_generic_hmac_missing_signature_header(self, mock_config, sample_body):
        """Test missing signature header."""
        with patch("src.security.validators.generic_hmac_validator.get_config", return_value=mock_config):
            headers = {}

            with pytest.raises(SignatureValidationError) as exc_info:
                generic_hmac_validator.validate(headers, sample_body)

            assert "missing" in exc_info.value.message.lower()

    def test_generic_hmac_authorization_without_bearer(self, mock_config, sample_body):
        """Test Authorization header without Bearer prefix is treated as missing."""
        with patch("src.security.validators.generic_hmac_validator.get_config", return_value=mock_config):
            headers = {
                "authorization": "Basic some_value"
            }

            with pytest.raises(SignatureValidationError) as exc_info:
                generic_hmac_validator.validate(headers, sample_body)

            assert "missing" in exc_info.value.message.lower()


# ============================================================================
# Signature Validator Factory Tests
# ============================================================================

class TestSignatureValidatorFactory:
    """Tests for signature validator factory and auto-detection."""

    def test_detect_mailgun_provider(self):
        """Test auto-detection of Mailgun provider."""
        headers = {
            "x-mailgun-signature": "timestamp=123 token=abc signature=def",
            "other-header": "value"
        }

        provider = signature_validator.detect_provider(headers)
        assert provider == "mailgun"

    def test_detect_mailgun_provider_alternative_header(self):
        """Test auto-detection of Mailgun provider using alternative header."""
        headers = {
            "x-mailgun-event-data": "some_data",
            "other-header": "value"
        }

        provider = signature_validator.detect_provider(headers)
        assert provider == "mailgun"

    def test_detect_sendgrid_provider(self):
        """Test auto-detection of SendGrid provider."""
        headers = {
            "x-sendgrid-signature": "some_signature",
            "x-sendgrid-timestamp": "1234567890"
        }

        provider = signature_validator.detect_provider(headers)
        assert provider == "sendgrid"

    def test_detect_generic_provider_x_signature(self):
        """Test auto-detection of generic provider with X-Signature header."""
        headers = {
            "x-signature": "some_signature",
            "other-header": "value"
        }

        provider = signature_validator.detect_provider(headers)
        assert provider == "generic"

    def test_detect_generic_provider_authorization(self):
        """Test auto-detection of generic provider with Authorization header."""
        headers = {
            "authorization": "Bearer some_signature",
            "other-header": "value"
        }

        provider = signature_validator.detect_provider(headers)
        assert provider == "generic"

    def test_detect_unknown_provider_defaults_to_generic(self):
        """Test that unknown provider defaults to generic."""
        headers = {
            "content-type": "application/json",
            "user-agent": "custom-client"
        }

        provider = signature_validator.detect_provider(headers)
        assert provider == "generic"

    def test_validate_signature_mailgun(self, mock_config, sample_body):
        """Test validate_signature routes to Mailgun validator."""
        with patch("src.security.validators.mailgun_validator.get_config", return_value=mock_config):
            with patch("src.security.validators.mailgun_validator.validate") as mock_mailgun:
                mock_mailgun.return_value = True

                timestamp = str(int(time.time()))
                token = "test_token_abc123"
                message = timestamp + token
                expected_signature = hmac.new(
                    mock_config.webhook_secret_key.encode("utf-8"),
                    message.encode("utf-8"),
                    hashlib.sha256
                ).hexdigest()

                headers = {
                    "X-Mailgun-Signature": f"timestamp={timestamp} token={token} signature={expected_signature}"
                }

                with patch("src.security.signature_validator.get_config", return_value=mock_config):
                    result = signature_validator.validate_signature(headers, sample_body)

                assert result is True

    def test_validate_signature_sendgrid(self, mock_config, sample_body):
        """Test validate_signature routes to SendGrid validator."""
        with patch("src.security.validators.sendgrid_validator.get_config", return_value=mock_config):
            with patch("src.security.validators.sendgrid_validator.validate") as mock_sendgrid:
                mock_sendgrid.return_value = True

                headers = {
                    "X-SendGrid-Signature": "some_signature",
                    "X-SendGrid-Timestamp": str(int(time.time()))
                }

                with patch("src.security.signature_validator.get_config", return_value=mock_config):
                    result = signature_validator.validate_signature(headers, sample_body)

                assert result is True

    def test_validate_signature_generic(self, mock_config, sample_body):
        """Test validate_signature routes to generic HMAC validator."""
        with patch("src.security.validators.generic_hmac_validator.get_config", return_value=mock_config):
            with patch("src.security.validators.generic_hmac_validator.validate") as mock_generic:
                mock_generic.return_value = True

                expected_signature = hmac.new(
                    mock_config.webhook_secret_key.encode("utf-8"),
                    sample_body,
                    hashlib.sha256
                ).hexdigest()

                headers = {
                    "X-Signature": expected_signature
                }

                with patch("src.security.signature_validator.get_config", return_value=mock_config):
                    result = signature_validator.validate_signature(headers, sample_body)

                assert result is True

    def test_validate_signature_disabled(self, mock_config, sample_body):
        """Test that validation can be bypassed via configuration."""
        mock_config.signature_validation_enabled = False

        with patch("src.security.signature_validator.get_config", return_value=mock_config):
            # Should return True without validating anything
            result = signature_validator.validate_signature({}, sample_body)
            assert result is True

    def test_validate_signature_error_propagates(self, mock_config, sample_body):
        """Test that validation errors are properly propagated."""
        with patch("src.security.validators.mailgun_validator.get_config", return_value=mock_config):
            headers = {
                "X-Mailgun-Signature": "invalid_format"
            }

            with patch("src.security.signature_validator.get_config", return_value=mock_config):
                with pytest.raises(SignatureValidationError):
                    signature_validator.validate_signature(headers, sample_body)


# ============================================================================
# Integration Tests
# ============================================================================

class TestSignatureValidationIntegration:
    """Integration tests for complete signature validation flow."""

    def test_mailgun_complete_flow(self, webhook_secret_key):
        """Test complete Mailgun signature validation flow."""
        body = b'{"from": "sender@example.com", "subject": "Test"}'
        timestamp = str(int(time.time()))
        token = "test_token_12345"

        # Create valid signature
        message = timestamp + token
        signature = hmac.new(
            webhook_secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "X-Mailgun-Signature": f"timestamp={timestamp} token={token} signature={signature}"
        }

        # Set up config
        config = MagicMock()
        config.webhook_secret_key = webhook_secret_key
        config.signature_validation_enabled = True

        with patch("src.security.signature_validator.get_config", return_value=config):
            with patch("src.security.validators.mailgun_validator.get_config", return_value=config):
                result = signature_validator.validate_signature(headers, body)
                assert result is True

    def test_generic_hmac_complete_flow(self, webhook_secret_key):
        """Test complete generic HMAC validation flow."""
        body = b'{"from": "sender@example.com", "subject": "Test"}'

        # Create valid signature
        signature = hmac.new(
            webhook_secret_key.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()

        headers = {
            "X-Signature": signature
        }

        # Set up config
        config = MagicMock()
        config.webhook_secret_key = webhook_secret_key
        config.signature_validation_enabled = True

        with patch("src.security.signature_validator.get_config", return_value=config):
            with patch("src.security.validators.generic_hmac_validator.get_config", return_value=config):
                result = signature_validator.validate_signature(headers, body)
                assert result is True

    def test_signature_validation_with_different_body_sizes(self, webhook_secret_key):
        """Test signature validation with various body sizes."""
        # Set up config
        config = MagicMock()
        config.webhook_secret_key = webhook_secret_key
        config.signature_validation_enabled = True

        # Test with small body
        small_body = b'{"test": "data"}'
        signature = hmac.new(
            webhook_secret_key.encode("utf-8"),
            small_body,
            hashlib.sha256
        ).hexdigest()

        headers_small = {"X-Signature": signature}

        with patch("src.security.signature_validator.get_config", return_value=config):
            with patch("src.security.validators.generic_hmac_validator.get_config", return_value=config):
                result = signature_validator.validate_signature(headers_small, small_body)
                assert result is True

        # Test with large body
        large_body = b'{"data": "' + (b'x' * 10000) + b'"}'
        signature = hmac.new(
            webhook_secret_key.encode("utf-8"),
            large_body,
            hashlib.sha256
        ).hexdigest()

        headers_large = {"X-Signature": signature}

        with patch("src.security.signature_validator.get_config", return_value=config):
            with patch("src.security.validators.generic_hmac_validator.get_config", return_value=config):
                result = signature_validator.validate_signature(headers_large, large_body)
                assert result is True
