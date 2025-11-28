"""Signature validation middleware - Layer 4 of security stack.

Validates webhook request signatures using provider-specific validators.
Only applies to /webhook/* endpoints.
Bypasses validation if SIGNATURE_VALIDATION_ENABLED=false.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Awaitable
from src.utils.logger import get_logger
from src.config import get_config

logger = get_logger(__name__)


class SignatureValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate webhook request signatures.

    Validates signatures as the final security layer after IP whitelist
    and rate limiting. Only applies to /webhook/* endpoints.
    Sets request.state.signature_valid = True for valid signatures.
    """

    def __init__(self, app: ASGIApp, signature_validator, ban_manager, security_logger=None):
        """Initialize signature validation middleware.

        Args:
            app: FastAPI application
            signature_validator: SignatureValidator instance or module with validate_signature function
            ban_manager: BanManager instance for tracking failures
            security_logger: SecurityLogger instance (optional, for event logging)
        """
        super().__init__(app)
        self.signature_validator = signature_validator
        self.ban_manager = ban_manager
        self.security_logger = security_logger
        self.config = get_config()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Validate request signature.

        Args:
            request: HTTP request
            call_next: Next middleware/route handler

        Returns:
            Response with 401 if signature invalid, otherwise processes request
        """
        endpoint = request.url.path

        # Only apply signature validation to /webhook/* endpoints
        if not endpoint.startswith("/webhook/"):
            # Not a webhook endpoint - skip validation
            return await call_next(request)

        # Check if signature validation is enabled
        if not self.config.signature_validation_enabled:
            logger.debug(
                "Signature validation disabled, bypassing",
                extra={"endpoint": endpoint}
            )
            # Validation disabled - set as valid and continue
            request.state.signature_valid = True
            return await call_next(request)

        # Get IP address from request state
        ip_address = getattr(request.state, "ip_address", None)
        if not ip_address:
            ip_address = self._extract_client_ip(request)
            request.state.ip_address = ip_address

        # Read request body for signature validation
        # We need to read the body, validate, then put it back for the handler
        body = await request.body()

        # Get request headers
        headers = dict(request.headers)

        # Validate signature
        is_valid = self.signature_validator.validate_signature(headers, body)

        if not is_valid:
            logger.warning(
                "Signature validation failed",
                extra={
                    "event_type": "signature_validation_failed",
                    "ip_address": ip_address,
                    "endpoint": endpoint,
                }
            )

            # Increment ban failure counter
            self.ban_manager.record_failure(ip_address)

            # Log security event if logger available
            if self.security_logger:
                provider = self._detect_provider(headers)
                await self.security_logger.log_signature_failure(
                    ip_address,
                    endpoint,
                    headers,
                    {"provider_detected": provider},
                )

            # Check if IP should be banned after this violation
            if self.ban_manager.should_ban_ip(ip_address):
                self.ban_manager.ban_ip(ip_address, "signature_validation_failures")
                logger.warning(
                    "IP banned due to signature validation failures",
                    extra={
                        "event_type": "ip_banned",
                        "ip_address": ip_address,
                        "reason": "signature_validation_failures",
                        "attempt_count": self.ban_manager.get_failure_count(ip_address),
                    }
                )

            # Return 401 Unauthorized
            return Response(
                content='{"error": "Unauthorized", "code": "INVALID_SIGNATURE"}',
                status_code=401,
                media_type="application/json",
            )

        # Signature valid - set flag and continue
        logger.debug(
            "Signature validation successful",
            extra={
                "ip_address": ip_address,
                "endpoint": endpoint,
            }
        )
        request.state.signature_valid = True

        # Continue to next middleware/handler
        # Create a new request with the body since we consumed it
        request._body = body
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

    def _detect_provider(self, headers: dict) -> str:
        """Detect email provider from request headers.

        Args:
            headers: Request headers

        Returns:
            Provider name (mailgun, sendgrid, generic)
        """
        normalized = {k.lower(): v for k, v in headers.items()}

        if "x-mailgun-signature" in normalized:
            return "mailgun"
        if "x-sendgrid-signature" in normalized:
            return "sendgrid"

        return "generic"
