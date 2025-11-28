"""IP whitelist middleware - Layer 2 of security stack.

Enforces IP allowlist after bans are checked.
Logs whitelist misses and increments ban failure counter.
Bypasses /health endpoint.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Awaitable
from src.utils.logger import get_logger
from src.utils.exceptions import IPNotWhitelistedError

logger = get_logger(__name__)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce IP allowlist.

    Checks if client IP is in the allowed list. Non-whitelisted IPs
    are rejected with 403. Increments failure counter for ban tracking.
    Bypasses /health endpoint to prevent monitoring lockout.
    """

    def __init__(self, app: ASGIApp, ip_allowlist_manager, ban_manager, security_logger=None):
        """Initialize IP whitelist middleware.

        Args:
            app: FastAPI application
            ip_allowlist_manager: IPAllowlistManager instance
            ban_manager: BanManager instance for tracking failures
            security_logger: SecurityLogger instance (optional, for event logging)
        """
        super().__init__(app)
        self.ip_allowlist_manager = ip_allowlist_manager
        self.ban_manager = ban_manager
        self.security_logger = security_logger

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Check if client IP is in allowlist.

        Args:
            request: HTTP request
            call_next: Next middleware/route handler

        Returns:
            Response with 403 if IP not allowed, otherwise processes request
        """
        # Get IP address from request state (set by IPBanMiddleware)
        ip_address = getattr(request.state, "ip_address", None)
        if not ip_address:
            # Fallback extraction if not in state
            ip_address = self._extract_client_ip(request)
            request.state.ip_address = ip_address

        endpoint = request.url.path

        # Bypass whitelist check for /health endpoint
        if endpoint == "/health":
            return await call_next(request)

        # Check if IP is allowed
        if not self.ip_allowlist_manager.is_ip_allowed(ip_address):
            logger.warning(
                "IP not whitelisted",
                extra={
                    "event_type": "ip_not_whitelisted",
                    "ip_address": ip_address,
                    "endpoint": endpoint,
                }
            )

            # Increment ban failure counter
            self.ban_manager.record_failure(ip_address)

            # Log security event if logger available
            if self.security_logger:
                await self.security_logger.log_ip_not_whitelisted(ip_address, endpoint)

            # Return 403 Forbidden
            return Response(
                content='{"error": "Access denied", "code": "IP_NOT_WHITELISTED"}',
                status_code=403,
                media_type="application/json",
            )

        # IP is allowed - continue to next middleware
        return await call_next(request)

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
