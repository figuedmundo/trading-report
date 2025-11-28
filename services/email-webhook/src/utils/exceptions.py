"""Custom exception classes for email-webhook service.

Provides typed exceptions for different security error scenarios with context.
Maps exceptions to appropriate HTTP status codes.
"""


class SecurityError(Exception):
    """Base exception for security-related errors in webhook service."""

    # Default HTTP status code for this error
    HTTP_STATUS_CODE = 400

    def __init__(
        self,
        message: str,
        error_code: str = "SECURITY_ERROR",
        context: dict = None,
    ):
        """Initialize security exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            context: Additional context dict for logging (not exposed to client)
        """
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)


class SignatureValidationError(SecurityError):
    """Raised when request signature validation fails."""

    HTTP_STATUS_CODE = 401

    def __init__(self, message: str, context: dict = None):
        """Initialize signature validation error."""
        super().__init__(
            message,
            error_code="INVALID_SIGNATURE",
            context=context
        )


class IPNotWhitelistedError(SecurityError):
    """Raised when IP address is not in whitelist."""

    HTTP_STATUS_CODE = 403

    def __init__(self, message: str, context: dict = None):
        """Initialize IP not whitelisted error."""
        super().__init__(
            message,
            error_code="IP_NOT_WHITELISTED",
            context=context
        )


class RateLimitExceededError(SecurityError):
    """Raised when rate limit is exceeded."""

    HTTP_STATUS_CODE = 429

    def __init__(self, message: str, context: dict = None):
        """Initialize rate limit exceeded error."""
        super().__init__(
            message,
            error_code="RATE_LIMIT_EXCEEDED",
            context=context
        )


class IPBannedError(SecurityError):
    """Raised when IP address is banned."""

    HTTP_STATUS_CODE = 403

    def __init__(self, message: str, context: dict = None):
        """Initialize IP banned error."""
        super().__init__(
            message,
            error_code="IP_BANNED",
            context=context
        )


class ConnectionThrottledError(SecurityError):
    """Raised when connection is throttled due to security concerns."""

    HTTP_STATUS_CODE = 503

    def __init__(self, message: str, context: dict = None):
        """Initialize connection throttled error."""
        super().__init__(
            message,
            error_code="CONNECTION_THROTTLED",
            context=context
        )


class DatabaseError(SecurityError):
    """Raised when database operation fails."""

    HTTP_STATUS_CODE = 500

    def __init__(self, message: str, context: dict = None):
        """Initialize database error."""
        super().__init__(
            message,
            error_code="DATABASE_ERROR",
            context=context
        )


# Map exception types to HTTP status codes for middleware error handlers
EXCEPTION_TO_STATUS_CODE = {
    SignatureValidationError: 401,
    IPNotWhitelistedError: 403,
    RateLimitExceededError: 429,
    IPBannedError: 403,
    ConnectionThrottledError: 503,
    DatabaseError: 500,
}
