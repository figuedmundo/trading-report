"""
Custom exception classes for scraper service.

Provides typed exceptions for different error scenarios with context.
"""


class ScraperException(Exception):
    """Base exception for scraper service."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        context: dict = None,
    ):
        """
        Initialize scraper exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            context: Additional context dict
        """
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)


class LoginError(ScraperException):
    """Raised when login fails."""

    def __init__(self, message: str, context: dict = None):
        """Initialize login error."""
        super().__init__(message, error_code="LOGIN_ERROR", context=context)


class NavigationError(ScraperException):
    """Raised when page navigation fails."""

    def __init__(self, message: str, context: dict = None):
        """Initialize navigation error."""
        super().__init__(message, error_code="NAVIGATION_ERROR", context=context)


class ExtractionError(ScraperException):
    """Raised when content extraction fails."""

    def __init__(self, message: str, context: dict = None):
        """Initialize extraction error."""
        super().__init__(message, error_code="EXTRACTION_ERROR", context=context)


class ImageDownloadError(ScraperException):
    """Raised when image download fails."""

    def __init__(self, message: str, context: dict = None):
        """Initialize image download error."""
        super().__init__(message, error_code="IMAGE_DOWNLOAD_ERROR", context=context)


class TimeoutError(ScraperException):
    """Raised when operation times out."""

    def __init__(self, message: str, context: dict = None):
        """Initialize timeout error."""
        super().__init__(message, error_code="TIMEOUT_ERROR", context=context)


class CredentialError(ScraperException):
    """Raised when credentials are missing or invalid."""

    def __init__(self, message: str, context: dict = None):
        """Initialize credential error."""
        super().__init__(message, error_code="CREDENTIAL_ERROR", context=context)
