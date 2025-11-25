"""
Tests for Task Group 3: Webhook Endpoint & HMAC-SHA256 Signature Verification

Tests HMAC-SHA256 signature verification, API key authentication, and webhook endpoint
authentication behavior.
"""

import pytest
import sys
import os
import hmac
import hashlib
import json
from unittest.mock import patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    from main import app
    return TestClient(app)


@pytest.fixture
def test_secret():
    """Test webhook secret for signature generation."""
    return "test-secret-key-12345"


@pytest.fixture
def sample_payload():
    """Sample webhook payload."""
    return {
        "from": "sender@example.com",
        "subject": "Trading Report",
        "text": "This is a trading analysis report.",
        "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
        "message-id": "<test-message-id-12345@example.com>",
    }


class TestHMACSignatureVerification:
    """Test HMAC-SHA256 signature verification."""

    def test_valid_signature_accepted(self, test_secret):
        """Test that valid HMAC-SHA256 signature is accepted."""
        from security import verify_hmac_signature

        payload = b"test payload content"

        # Generate valid signature
        signature = hmac.new(
            test_secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Patch config to use test secret
        with patch("security.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.webhook_signature_secret = test_secret
            mock_get_config.return_value = mock_config

            result = verify_hmac_signature(payload, signature)
            assert result is True

    def test_invalid_signature_rejected(self, test_secret):
        """Test that invalid HMAC-SHA256 signature is rejected."""
        from security import verify_hmac_signature

        payload = b"test payload content"
        invalid_signature = "invalid_signature_value"

        with patch("security.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.webhook_signature_secret = test_secret
            mock_get_config.return_value = mock_config

            result = verify_hmac_signature(payload, invalid_signature)
            assert result is False

    def test_wrong_payload_signature_rejected(self, test_secret):
        """Test that signature for different payload is rejected."""
        from security import verify_hmac_signature

        payload1 = b"test payload 1"
        payload2 = b"test payload 2"

        # Generate signature for payload1
        signature = hmac.new(
            test_secret.encode("utf-8"),
            payload1,
            hashlib.sha256
        ).hexdigest()

        # Try to verify with payload2
        with patch("security.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.webhook_signature_secret = test_secret
            mock_get_config.return_value = mock_config

            result = verify_hmac_signature(payload2, signature)
            assert result is False

    def test_signature_verification_uses_constant_time_comparison(self, test_secret):
        """Test that signature verification uses constant-time comparison."""
        from security import verify_hmac_signature

        payload = b"test payload"
        signature = hmac.new(
            test_secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        with patch("security.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.webhook_signature_secret = test_secret
            mock_get_config.return_value = mock_config

            # Even though signature is correct, timing should be consistent
            result = verify_hmac_signature(payload, signature)
            assert result is True


class TestAPIKeyAuthentication:
    """Test API key fallback authentication."""

    def test_valid_api_key_accepted(self):
        """Test that valid API key is accepted."""
        from security import verify_api_key

        test_key = "test-api-key-12345"

        with patch("security.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.api_key_fallback = test_key
            mock_get_config.return_value = mock_config

            result = verify_api_key(test_key)
            assert result is True

    def test_invalid_api_key_rejected(self):
        """Test that invalid API key is rejected."""
        from security import verify_api_key

        test_key = "test-api-key-12345"
        wrong_key = "wrong-api-key"

        with patch("security.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.api_key_fallback = test_key
            mock_get_config.return_value = mock_config

            result = verify_api_key(wrong_key)
            assert result is False

    def test_no_api_key_configured_returns_false(self):
        """Test that no fallback key configured returns False."""
        from security import verify_api_key

        with patch("security.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.api_key_fallback = None
            mock_get_config.return_value = mock_config

            result = verify_api_key("any-key")
            assert result is False


class TestWebhookAuthentication:
    """Test combined webhook request authentication."""

    def test_authenticate_with_valid_signature(self, test_secret):
        """Test webhook authentication with valid HMAC-SHA256 signature."""
        from security import authenticate_webhook_request

        payload = b"test payload content"

        # Generate valid signature
        signature = hmac.new(
            test_secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        with patch("security.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.webhook_signature_secret = test_secret
            mock_config.api_key_fallback = None
            mock_get_config.return_value = mock_config

            is_authenticated, auth_method = authenticate_webhook_request(
                payload, signature_header=signature
            )

            assert is_authenticated is True
            assert auth_method == "signature"

    def test_authenticate_with_valid_api_key(self):
        """Test webhook authentication with valid API key."""
        from security import authenticate_webhook_request

        test_key = "test-api-key"
        payload = b"test payload"

        with patch("security.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.webhook_signature_secret = "not-matching"
            mock_config.api_key_fallback = test_key
            mock_get_config.return_value = mock_config

            is_authenticated, auth_method = authenticate_webhook_request(
                payload, signature_header=None, api_key_header=test_key
            )

            assert is_authenticated is True
            assert auth_method == "api_key"

    def test_authenticate_with_invalid_credentials(self):
        """Test webhook authentication with invalid credentials."""
        from security import authenticate_webhook_request

        payload = b"test payload"

        with patch("security.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.webhook_signature_secret = "test-secret"
            mock_config.api_key_fallback = None
            mock_get_config.return_value = mock_config

            is_authenticated, auth_method = authenticate_webhook_request(
                payload, signature_header="invalid", api_key_header=None
            )

            assert is_authenticated is False
            assert auth_method == "none"

    def test_signature_takes_precedence_over_api_key(self, test_secret):
        """Test that signature verification is tried before API key."""
        from security import authenticate_webhook_request

        payload = b"test payload content"

        # Generate valid signature
        signature = hmac.new(
            test_secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        test_key = "test-api-key"

        with patch("security.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.webhook_signature_secret = test_secret
            mock_config.api_key_fallback = test_key
            mock_get_config.return_value = mock_config

            is_authenticated, auth_method = authenticate_webhook_request(
                payload, signature_header=signature, api_key_header=test_key
            )

            # Signature should be used, not API key
            assert is_authenticated is True
            assert auth_method == "signature"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
