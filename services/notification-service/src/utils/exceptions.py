"""
Custom exception classes for notification service.

Provides typed exceptions for different error scenarios with context.
"""


class NotificationError(Exception):
    """Base exception for notification service."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        context: dict = None,
    ):
        """
        Initialize notification exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            context: Additional context dict
        """
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.error_code}: {self.message}"


class ChannelError(NotificationError):
    """Raised when channel operation fails."""

    def __init__(self, message: str, context: dict = None):
        """Initialize channel error."""
        super().__init__(message, error_code="CHANNEL_ERROR", context=context)


class TemplateError(NotificationError):
    """Raised when template rendering fails."""

    def __init__(self, message: str, context: dict = None):
        """Initialize template error."""
        super().__init__(message, error_code="TEMPLATE_ERROR", context=context)


class ConfigurationError(NotificationError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, context: dict = None):
        """Initialize configuration error."""
        super().__init__(message, error_code="CONFIGURATION_ERROR", context=context)


class RateLimitError(NotificationError):
    """Raised when rate limit exceeded."""

    def __init__(self, message: str, context: dict = None):
        """Initialize rate limit error."""
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", context=context)


class ValidationError(NotificationError):
    """Raised when validation fails."""

    def __init__(self, message: str, context: dict = None):
        """Initialize validation error."""
        super().__init__(message, error_code="VALIDATION_ERROR", context=context)


class DatabaseError(NotificationError):
    """Raised when database operation fails."""

    def __init__(self, message: str, context: dict = None):
        """Initialize database error."""
        super().__init__(message, error_code="DATABASE_ERROR", context=context)
