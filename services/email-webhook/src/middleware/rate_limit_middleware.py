"""Rate limit middleware - Layer 3 of security stack.

Enforces per-IP and global rate limits.
Returns 429 with Retry-After header if exceeded.
Adds rate limit headers to all responses.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Awaitable
import time
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting.

    Checks rate limits after IP allowlist validation.
    Returns 429 with Retry-After header if limits exceeded.
    Adds X-RateLimit-* headers to all responses.
    Increments ban failure counter on violations.
    """

    def __init__(self, app: ASGIApp, rate_limiter, ban_manager, security_logger=None):
        """Initialize rate limit middleware.

        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance
            ban_manager: BanManager instance for tracking failures
            security_logger: SecurityLogger instance (optional, for event logging)
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.ban_manager = ban_manager
        self.security_logger = security_logger

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Check rate limits for the request.

        Args:
            request: HTTP request
            call_next: Next middleware/route handler

        Returns:
            Response with 429 if rate limited, otherwise processes request
        """
        # Get IP address from request state
        ip_address = getattr(request.state, "ip_address", None)
        if not ip_address:
            ip_address = self._extract_client_ip(request)
            request.state.ip_address = ip_address

        endpoint = request.url.path

        # Bypass rate limit check for /health endpoint
        if endpoint == "/health":
            return await call_next(request)

        # Check if request has valid signature (for authenticated multiplier)
        authenticated = getattr(request.state, "signature_valid", False)

        # Check rate limit
        allowed, metadata = self.rate_limiter.check_rate_limit(ip_address, authenticated)

        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "event_type": "rate_limit_exceeded",
                    "ip_address": ip_address,
                    "endpoint": endpoint,
                    "limit_type": metadata.get("limit_type"),
                    "reset_seconds": metadata.get("reset_seconds"),
                }
            )

            # Increment ban failure counter
            self.ban_manager.record_failure(ip_address)

            # Log security event if logger available
            if self.security_logger:
                await self.security_logger.log_rate_limit_exceeded(
                    ip_address,
                    endpoint,
                    metadata.get("limit_type"),
                    metadata.get("remaining", 0),
                )

            # Check if IP should be banned after this violation
            if self.ban_manager.should_ban_ip(ip_address):
                self.ban_manager.ban_ip(ip_address, "rate_limit_ban_threshold_exceeded")
                logger.warning(
                    "IP banned due to rate limit violations",
                    extra={
                        "event_type": "ip_banned",
                        "ip_address": ip_address,
                        "reason": "rate_limit_ban_threshold_exceeded",
                        "attempt_count": self.ban_manager.get_failure_count(ip_address),
                    }
                )

            # Return 429 Too Many Requests with Retry-After header
            reset_seconds = metadata.get("reset_seconds", 60)
            return Response(
                content='{"error": "Rate limit exceeded", "code": "RATE_LIMIT_EXCEEDED"}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(reset_seconds),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(metadata.get("reset_time", time.time()))),
                },
            )

        # Rate limit check passed - continue to next middleware
        # Also store metadata in request state for response headers
        request.state.rate_limit_metadata = metadata

        # Call next middleware/handler and add rate limit headers
        response = await call_next(request)

        # Add rate limit headers to response
        remaining = metadata.get("remaining", 0)
        reset_time = metadata.get("reset_time", time.time())

        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))

        return response

    def _extract_client_ip(self, request: Request) -> str:
        """Extract client IP from request.

        Args:
            request: HTTP request

        Returns:
            Client IP address as string
        """
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
            return ip_address

        if request.client:
            return request.client.host

        return "0.0.0.0"
