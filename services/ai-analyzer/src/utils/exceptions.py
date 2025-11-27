"""
Custom exception classes for AI analysis service.

Provides typed exceptions for different error scenarios with context.
"""


class AnalysisError(Exception):
    """Base exception for analysis service."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        context: dict = None,
    ):
        """
        Initialize analysis exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            context: Additional context dict
        """
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)


class LLMError(AnalysisError):
    """Raised when LLM API call fails."""

    def __init__(self, message: str, context: dict = None):
        """Initialize LLM error."""
        super().__init__(message, error_code="LLM_ERROR", context=context)


class InvalidResponseError(AnalysisError):
    """Raised when LLM returns malformed response."""

    def __init__(self, message: str, context: dict = None):
        """Initialize invalid response error."""
        super().__init__(message, error_code="INVALID_RESPONSE_ERROR", context=context)


class ConfigurationError(AnalysisError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, context: dict = None):
        """Initialize configuration error."""
        super().__init__(message, error_code="CONFIGURATION_ERROR", context=context)


class FallbackExtractionError(AnalysisError):
    """Raised when fallback keyword extraction fails."""

    def __init__(self, message: str, context: dict = None):
        """Initialize fallback extraction error."""
        super().__init__(message, error_code="FALLBACK_EXTRACTION_ERROR", context=context)


class DatabaseError(AnalysisError):
    """Raised when database operation fails."""

    def __init__(self, message: str, context: dict = None):
        """Initialize database error."""
        super().__init__(message, error_code="DATABASE_ERROR", context=context)
