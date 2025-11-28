"""IP ban middleware - Layer 1 of security stack.

Checks if a client IP is banned and rejects it immediately if so.
Sets request.state.ip_address for downstream middleware.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Awaitable
from src.utils.logger import get_logger
from src.utils.exceptions import IPBannedError

logger = get_logger(__name__)


class IPBanMiddleware(BaseHTTPMiddleware):
    """Middleware to check and block banned IPs.

    Executes first in the middleware chain to immediately reject
    banned IPs before any further processing.
    """

    def __init__(self, app: ASGIApp, ban_manager):
        """Initialize IP ban middleware.

        Args:
            app: FastAPI application
            ban_manager: BanManager instance for checking banned IPs
        """
        super().__init__(app)
        self.ban_manager = ban_manager

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Check if client IP is banned.

        Args:
            request: HTTP request
            call_next: Next middleware/route handler

        Returns:
            Response with 403 if IP is banned, otherwise processes request
        """
        # Extract client IP from headers or request connection
        ip_address = self._extract_client_ip(request)

        # Store IP in request state for downstream middleware
        request.state.ip_address = ip_address

        # Check if IP is banned
        if self.ban_manager.is_ip_banned(ip_address):
            logger.warning(
                "Banned IP attempted access",
                extra={
                    "event_type": "ip_banned",
                    "ip_address": ip_address,
                    "endpoint": request.url.path,
                }
            )

            # Return 403 Forbidden with minimal error message
            return Response(
                content='{"error": "Access denied", "code": "IP_BANNED"}',
                status_code=403,
                media_type="application/json",
            )

        # IP not banned - continue to next middleware
        return await call_next(request)

    def _extract_client_ip(self, request: Request) -> str:
        """Extract client IP from request.

        Checks X-Forwarded-For header first (for reverse proxy),
        then falls back to request.client.host.

        Args:
            request: HTTP request

        Returns:
            Client IP address as string
        """
        # Check X-Forwarded-For header (set by reverse proxy)
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # Take the first IP if multiple are present
            ip_address = x_forwarded_for.split(",")[0].strip()
            return ip_address

        # Fall back to direct client connection
        if request.client:
            return request.client.host

        # Fallback if no client info available
        return "0.0.0.0"
