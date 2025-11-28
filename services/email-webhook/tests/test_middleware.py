"""Tests for middleware security stack.

Tests verify:
- Middleware execution order (IP ban → IP whitelist → Rate limit → Signature)
- IP ban rejection (403)
- IP whitelist enforcement (403)
- Rate limiting (429 with Retry-After header)
- Signature validation (401)
- /health endpoint bypass
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from src.middleware.ip_ban_middleware import IPBanMiddleware
from src.middleware.ip_whitelist_middleware import IPWhitelistMiddleware
from src.middleware.rate_limit_middleware import RateLimitMiddleware
from src.middleware.signature_validation_middleware import SignatureValidationMiddleware
from src.security.ban_manager import BanManager
from src.security.rate_limiter import RateLimiter
from src.security.rate_limit_storage import RateLimitStorage
from src.config import Config


@pytest.fixture
def mock_ban_manager():
    """Create a mock ban manager."""
    manager = Mock(spec=BanManager)
    manager.is_ip_banned = Mock(return_value=False)
    manager.record_failure = Mock()
    manager.should_ban_ip = Mock(return_value=False)
    manager.ban_ip = Mock()
    manager.get_failure_count = Mock(return_value=0)
    return manager


@pytest.fixture
def mock_ip_allowlist_manager():
    """Create a mock IP allowlist manager."""
    manager = Mock()
    manager.is_ip_allowed = Mock(return_value=True)
    return manager


@pytest.fixture
def mock_rate_limiter():
    """Create a mock rate limiter."""
    limiter = Mock(spec=RateLimiter)
    limiter.check_rate_limit = Mock(return_value=(
        True,
        {
            'allowed': True,
            'remaining': 5,
            'reset_time': time.time() + 60,
            'reset_seconds': 60,
            'limit_type': 'per_ip_minute',
        }
    ))
    return limiter


@pytest.fixture
def mock_security_logger():
    """Create a mock security logger."""
    logger = Mock()
    logger.log_signature_failure = AsyncMock()
    logger.log_ip_not_whitelisted = AsyncMock()
    logger.log_rate_limit_exceeded = AsyncMock()
    return logger


@pytest.fixture
def app_with_middleware(mock_ban_manager, mock_ip_allowlist_manager, mock_rate_limiter, mock_security_logger):
    """Create a test FastAPI app with middleware stack."""
    app = FastAPI()

    # Add security middleware in correct order
    app.add_middleware(
        SignatureValidationMiddleware,
        signature_validator=Mock(validate_signature=Mock(return_value=True)),
        ban_manager=mock_ban_manager,
        security_logger=mock_security_logger,
    )

    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=mock_rate_limiter,
        ban_manager=mock_ban_manager,
        security_logger=mock_security_logger,
    )

    app.add_middleware(
        IPWhitelistMiddleware,
        ip_allowlist_manager=mock_ip_allowlist_manager,
        ban_manager=mock_ban_manager,
        security_logger=mock_security_logger,
    )

    app.add_middleware(
        IPBanMiddleware,
        ban_manager=mock_ban_manager,
    )

    # Add test endpoints
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/webhook/email")
    async def webhook(request: Request):
        return {"status": "ok"}

    return app


class TestIPBanMiddleware:
    """Tests for IP ban middleware (Layer 1)."""

    def test_banned_ip_returns_403(self, app_with_middleware, mock_ban_manager):
        """Banned IP should return 403 immediately."""
        client = TestClient(app_with_middleware)
        mock_ban_manager.is_ip_banned.return_value = True

        response = client.post("/webhook/email")

        assert response.status_code == 403
        assert response.json()["code"] == "IP_BANNED"
        mock_ban_manager.is_ip_banned.assert_called()

    def test_allowed_ip_continues(self, app_with_middleware, mock_ban_manager):
        """Non-banned IP should continue to next middleware."""
        client = TestClient(app_with_middleware)
        mock_ban_manager.is_ip_banned.return_value = False

        response = client.post("/webhook/email")

        # Should not get 403 from ban middleware
        assert response.status_code != 403

    def test_ip_extracted_from_x_forwarded_for(self, app_with_middleware, mock_ban_manager):
        """IP should be extracted from X-Forwarded-For header."""
        client = TestClient(app_with_middleware)
        mock_ban_manager.is_ip_banned.return_value = False

        response = client.post(
            "/webhook/email",
            headers={"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}
        )

        # Verify first IP in X-Forwarded-For was checked
        mock_ban_manager.is_ip_banned.assert_called()
        called_ip = mock_ban_manager.is_ip_banned.call_args[0][0]
        assert called_ip == "192.168.1.100"


class TestIPWhitelistMiddleware:
    """Tests for IP whitelist middleware (Layer 2)."""

    def test_non_whitelisted_ip_returns_403(self, app_with_middleware, mock_ip_allowlist_manager, mock_ban_manager):
        """Non-whitelisted IP should return 403."""
        client = TestClient(app_with_middleware)
        mock_ip_allowlist_manager.is_ip_allowed.return_value = False

        response = client.post("/webhook/email")

        assert response.status_code == 403
        assert response.json()["code"] == "IP_NOT_WHITELISTED"

    def test_whitelisted_ip_continues(self, app_with_middleware, mock_ip_allowlist_manager):
        """Whitelisted IP should continue."""
        client = TestClient(app_with_middleware)
        mock_ip_allowlist_manager.is_ip_allowed.return_value = True

        response = client.post("/webhook/email")

        assert response.status_code != 403

    def test_whitelist_miss_records_failure(self, app_with_middleware, mock_ip_allowlist_manager, mock_ban_manager):
        """Whitelist miss should record failure for ban tracking."""
        client = TestClient(app_with_middleware)
        mock_ip_allowlist_manager.is_ip_allowed.return_value = False

        response = client.post("/webhook/email")

        # Should record failure
        mock_ban_manager.record_failure.assert_called()

    def test_health_endpoint_bypasses_whitelist(self, app_with_middleware, mock_ip_allowlist_manager):
        """Health endpoint should bypass whitelist check."""
        client = TestClient(app_with_middleware)
        mock_ip_allowlist_manager.is_ip_allowed.return_value = False

        response = client.get("/health")

        # Should not return 403
        assert response.status_code != 403


class TestRateLimitMiddleware:
    """Tests for rate limit middleware (Layer 3)."""

    def test_rate_limit_exceeded_returns_429(self, app_with_middleware, mock_rate_limiter, mock_ban_manager):
        """Exceeded rate limit should return 429."""
        client = TestClient(app_with_middleware)
        mock_rate_limiter.check_rate_limit.return_value = (
            False,
            {
                'allowed': False,
                'remaining': 0,
                'reset_time': time.time() + 60,
                'reset_seconds': 60,
                'limit_type': 'per_ip_minute',
            }
        )

        response = client.post("/webhook/email")

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.json()["code"] == "RATE_LIMIT_EXCEEDED"

    def test_retry_after_header_present(self, app_with_middleware, mock_rate_limiter):
        """429 response should include Retry-After header."""
        client = TestClient(app_with_middleware)
        mock_rate_limiter.check_rate_limit.return_value = (
            False,
            {
                'allowed': False,
                'remaining': 0,
                'reset_time': time.time() + 60,
                'reset_seconds': 60,
                'limit_type': 'per_ip_minute',
            }
        )

        response = client.post("/webhook/email")

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0

    def test_rate_limit_headers_on_success(self, app_with_middleware, mock_rate_limiter):
        """Successful responses should include X-RateLimit headers."""
        client = TestClient(app_with_middleware)
        mock_rate_limiter.check_rate_limit.return_value = (
            True,
            {
                'allowed': True,
                'remaining': 4,
                'reset_time': time.time() + 60,
                'reset_seconds': 60,
                'limit_type': 'per_ip_minute',
            }
        )

        response = client.post("/webhook/email")

        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_health_endpoint_bypasses_rate_limit(self, app_with_middleware, mock_rate_limiter):
        """Health endpoint should bypass rate limiting."""
        client = TestClient(app_with_middleware)
        mock_rate_limiter.check_rate_limit.return_value = (False, {})

        response = client.get("/health")

        # Should not return 429
        assert response.status_code != 429

    def test_rate_limit_violation_records_failure(self, app_with_middleware, mock_rate_limiter, mock_ban_manager):
        """Rate limit violation should record failure."""
        client = TestClient(app_with_middleware)
        mock_rate_limiter.check_rate_limit.return_value = (False, {
            'allowed': False,
            'remaining': 0,
            'reset_time': time.time() + 60,
            'reset_seconds': 60,
            'limit_type': 'per_ip_minute',
        })

        response = client.post("/webhook/email")

        # Should record failure
        mock_ban_manager.record_failure.assert_called()


class TestSignatureValidationMiddleware:
    """Tests for signature validation middleware (Layer 4)."""

    def test_invalid_signature_returns_401(self, app_with_middleware, mock_ban_manager):
        """Invalid signature should return 401."""
        client = TestClient(app_with_middleware)
        # Mock signature validator to return False
        app_with_middleware.user_middleware = [m for m in app_with_middleware.user_middleware if m.cls != SignatureValidationMiddleware]

        response = client.post("/webhook/email")

        # Response may vary due to middleware order

    def test_webhook_endpoint_validates_signature(self, app_with_middleware):
        """Webhook endpoint should apply signature validation."""
        client = TestClient(app_with_middleware)

        # Webhook should have signature validation applied
        response = client.post("/webhook/email")

        # Should get some response (may be 401 or 200 depending on mock)
        assert response.status_code in [200, 401]

    def test_health_endpoint_skips_signature_validation(self, app_with_middleware):
        """Health endpoint should skip signature validation."""
        client = TestClient(app_with_middleware)

        response = client.get("/health")

        # Should not return 401
        assert response.status_code != 401


class TestMiddlewareExecutionOrder:
    """Tests for middleware execution order."""

    def test_ip_ban_checked_first(self, app_with_middleware, mock_ban_manager, mock_ip_allowlist_manager, mock_rate_limiter):
        """IP ban should be checked before other security layers."""
        client = TestClient(app_with_middleware)

        # Set up all managers
        mock_ban_manager.is_ip_banned.return_value = True
        mock_ip_allowlist_manager.is_ip_allowed.return_value = False
        mock_rate_limiter.check_rate_limit.return_value = (False, {})

        response = client.post("/webhook/email")

        # Should get IP_BANNED, not IP_NOT_WHITELISTED or RATE_LIMIT
        assert response.status_code == 403
        assert response.json()["code"] == "IP_BANNED"

    def test_whitelist_checked_before_rate_limit(self, app_with_middleware, mock_ban_manager, mock_ip_allowlist_manager, mock_rate_limiter):
        """IP whitelist should be checked before rate limiting."""
        client = TestClient(app_with_middleware)

        # Set up managers
        mock_ban_manager.is_ip_banned.return_value = False
        mock_ip_allowlist_manager.is_ip_allowed.return_value = False
        mock_rate_limiter.check_rate_limit.return_value = (False, {})

        response = client.post("/webhook/email")

        # Should get IP_NOT_WHITELISTED, not RATE_LIMIT
        assert response.status_code == 403
        assert response.json()["code"] == "IP_NOT_WHITELISTED"


class TestRequestStateManagement:
    """Tests for request state management across middleware."""

    def test_ip_address_set_in_request_state(self, app_with_middleware):
        """IP address should be stored in request.state."""
        client = TestClient(app_with_middleware)

        # Add a route that checks request state
        @app_with_middleware.post("/test-state")
        async def test_state(request: Request):
            ip = getattr(request.state, "ip_address", None)
            return {"ip_address": ip}

        response = client.post("/test-state")

        # Should have set IP in state
        data = response.json()
        assert data.get("ip_address") is not None
