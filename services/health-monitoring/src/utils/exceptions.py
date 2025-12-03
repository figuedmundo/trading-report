"""
Custom exception types for health monitoring service.

Provides structured exception hierarchy for different failure modes.
"""

from typing import Dict, Any, Optional


class HealthMonitoringError(Exception):
    """Base exception for health monitoring service."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize health monitoring error.

        Args:
            message: Error message
            error_code: Machine-readable error code
            context: Additional error context
        """
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)


class DatabaseError(HealthMonitoringError):
    """Exception for database-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "DATABASE_ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, context)


class HealthCheckError(HealthMonitoringError):
    """Exception for health check failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "HEALTH_CHECK_ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, context)


class ErrorLoggingError(HealthMonitoringError):
    """Exception for error logging failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "ERROR_LOGGING_ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, context)


class AlertGenerationError(HealthMonitoringError):
    """Exception for alert generation failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "ALERT_GENERATION_ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, context)


class ConfigurationError(HealthMonitoringError):
    """Exception for configuration errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "CONFIGURATION_ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, context)
