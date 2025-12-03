"""
Error logging service for centralizing error handling across microservices.

Provides structured error logging with context tracking.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from src.db.error_repository import ErrorRepository
from src.utils.logger import get_logger
from src.utils.exceptions import ErrorLoggingError

logger = get_logger(__name__)


class ErrorLogger:
    """Service for logging errors to database."""

    @staticmethod
    async def log_error(
        service_name: str,
        error_type: str,
        severity: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        source_report_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ) -> str:
        """
        Log an error with full context.

        Args:
            service_name: Name of the service where error occurred
            error_type: Type of error (e.g., login_failure, api_timeout)
            severity: Severity level (CRITICAL, ERROR, WARNING)
            message: Human-readable error message
            context: Additional context as dictionary (optional)
            source_report_id: Report ID affected by this error (optional)
            correlation_id: ID for tracing related errors across services (optional)
            stack_trace: Full stack trace for debugging (optional)

        Returns:
            UUID of logged error

        Raises:
            ErrorLoggingError: If logging fails
        """
        try:
            # Validate severity
            valid_severities = {"CRITICAL", "ERROR", "WARNING"}
            if severity not in valid_severities:
                raise ValueError(f"Invalid severity: {severity}")

            # Log to application logger
            logger.error(
                f"Error: service={service_name}, type={error_type}, "
                f"severity={severity}, message={message}",
                extra={
                    "service_name": service_name,
                    "error_type": error_type,
                    "severity": severity,
                    "correlation_id": correlation_id,
                    "source_report_id": source_report_id,
                    "context": context,
                },
            )

            # Log to database
            error_id = await ErrorRepository.log_error(
                service_name=service_name,
                error_type=error_type,
                severity=severity,
                message=message,
                context=context,
                source_report_id=source_report_id,
                correlation_id=correlation_id,
                stack_trace=stack_trace,
            )

            return error_id

        except Exception as e:
            logger.error(f"Failed to log error: {str(e)}")
            raise ErrorLoggingError(
                f"Failed to log error: {str(e)}",
                context={
                    "service_name": service_name,
                    "error_type": error_type,
                    "severity": severity,
                },
            )

    @staticmethod
    async def log_critical(
        service_name: str,
        error_type: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        source_report_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ) -> str:
        """Log a CRITICAL error."""
        return await ErrorLogger.log_error(
            service_name=service_name,
            error_type=error_type,
            severity="CRITICAL",
            message=message,
            context=context,
            source_report_id=source_report_id,
            correlation_id=correlation_id,
            stack_trace=stack_trace,
        )

    @staticmethod
    async def log_error_msg(
        service_name: str,
        error_type: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        source_report_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ) -> str:
        """Log an ERROR level error."""
        return await ErrorLogger.log_error(
            service_name=service_name,
            error_type=error_type,
            severity="ERROR",
            message=message,
            context=context,
            source_report_id=source_report_id,
            correlation_id=correlation_id,
            stack_trace=stack_trace,
        )

    @staticmethod
    async def log_warning(
        service_name: str,
        error_type: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        source_report_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """Log a WARNING level error."""
        return await ErrorLogger.log_error(
            service_name=service_name,
            error_type=error_type,
            severity="WARNING",
            message=message,
            context=context,
            source_report_id=source_report_id,
            correlation_id=correlation_id,
        )
