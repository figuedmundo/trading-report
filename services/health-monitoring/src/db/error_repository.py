"""
Error log data access layer.

Handles storage and retrieval of error logs from PostgreSQL.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import uuid
import traceback

from src.db.connection import get_db_connection
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseError

logger = get_logger(__name__)


class ErrorRepository:
    """Repository for error log data operations."""

    @staticmethod
    async def log_error(
        service_name: str,
        error_type: str,
        severity: str,
        message: str,
        context: Optional[Dict] = None,
        source_report_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ) -> str:
        """
        Log an error to the database.

        Args:
            service_name: Name of the service where error occurred
            error_type: Type of error (e.g., login_failure, api_timeout)
            severity: Severity level (CRITICAL, ERROR, WARNING)
            message: Error message
            context: Additional context as dictionary
            source_report_id: Report ID affected by error (if applicable)
            correlation_id: Correlation ID for tracing
            stack_trace: Full stack trace

        Returns:
            UUID of logged error

        Raises:
            DatabaseError: If logging fails
        """
        try:
            error_id = str(uuid.uuid4())
            error_timestamp = datetime.now(timezone.utc)

            # Validate severity
            valid_severities = {"CRITICAL", "ERROR", "WARNING"}
            if severity not in valid_severities:
                raise ValueError(f"Invalid severity: {severity}")

            async with get_db_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO error_logs
                    (id, error_timestamp, service_name, error_type, severity,
                     message, context_json, source_report_id, stack_trace,
                     correlation_id, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    error_id,
                    error_timestamp,
                    service_name,
                    error_type,
                    severity,
                    message,
                    context or {},
                    source_report_id,
                    stack_trace,
                    correlation_id,
                    error_timestamp,
                )

            logger.error(
                f"Error logged: service={service_name}, type={error_type}, "
                f"severity={severity}"
            )
            return error_id

        except Exception as e:
            logger.error(f"Failed to log error: {str(e)}")
            raise DatabaseError(
                f"Failed to log error: {str(e)}",
                context={"service_name": service_name, "error": str(e)},
            )

    @staticmethod
    async def get_recent_errors(
        severity: Optional[str] = None,
        service: Optional[str] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Retrieve recent errors with optional filtering.

        Args:
            severity: Filter by severity (CRITICAL, ERROR, WARNING)
            service: Filter by service name
            hours: Number of hours to look back
            limit: Maximum number of records to return

        Returns:
            List of error log records

        Raises:
            DatabaseError: If retrieval fails
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            query = """
                SELECT
                    id, error_timestamp, service_name, error_type, severity,
                    message, context_json, source_report_id, stack_trace,
                    correlation_id, created_at
                FROM error_logs
                WHERE error_timestamp >= $1
            """
            params = [cutoff_time]
            param_count = 1

            if severity:
                param_count += 1
                query += f" AND severity = ${param_count}"
                params.append(severity)

            if service:
                param_count += 1
                query += f" AND service_name = ${param_count}"
                params.append(service)

            query += f" ORDER BY error_timestamp DESC LIMIT ${param_count + 1}"
            params.append(limit)

            async with get_db_connection() as conn:
                rows = await conn.fetch(query, *params)

            result = []
            for row in rows:
                result.append({
                    "id": str(row["id"]),
                    "error_timestamp": row["error_timestamp"],
                    "service_name": row["service_name"],
                    "error_type": row["error_type"],
                    "severity": row["severity"],
                    "message": row["message"],
                    "context_json": row["context_json"],
                    "source_report_id": str(row["source_report_id"]) if row["source_report_id"] else None,
                    "stack_trace": row["stack_trace"],
                    "correlation_id": row["correlation_id"],
                    "created_at": row["created_at"],
                })

            return result

        except Exception as e:
            logger.error(f"Failed to retrieve errors: {str(e)}")
            raise DatabaseError(
                f"Failed to retrieve errors: {str(e)}",
                context={"error": str(e)},
            )

    @staticmethod
    async def get_error_by_id(error_id: str) -> Optional[Dict]:
        """
        Retrieve a single error by ID.

        Args:
            error_id: UUID of the error

        Returns:
            Error record or None if not found

        Raises:
            DatabaseError: If retrieval fails
        """
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        id, error_timestamp, service_name, error_type, severity,
                        message, context_json, source_report_id, stack_trace,
                        correlation_id, created_at
                    FROM error_logs
                    WHERE id = $1
                    """,
                    error_id,
                )

            if not row:
                return None

            return {
                "id": str(row["id"]),
                "error_timestamp": row["error_timestamp"],
                "service_name": row["service_name"],
                "error_type": row["error_type"],
                "severity": row["severity"],
                "message": row["message"],
                "context_json": row["context_json"],
                "source_report_id": str(row["source_report_id"]) if row["source_report_id"] else None,
                "stack_trace": row["stack_trace"],
                "correlation_id": row["correlation_id"],
                "created_at": row["created_at"],
            }

        except Exception as e:
            logger.error(f"Failed to retrieve error {error_id}: {str(e)}")
            raise DatabaseError(
                f"Failed to retrieve error: {str(e)}",
                context={"error_id": error_id, "error": str(e)},
            )

    @staticmethod
    async def get_errors_by_correlation_id(correlation_id: str) -> List[Dict]:
        """
        Retrieve all errors with a specific correlation ID.

        Args:
            correlation_id: Correlation ID to search for

        Returns:
            List of related error records

        Raises:
            DatabaseError: If retrieval fails
        """
        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        id, error_timestamp, service_name, error_type, severity,
                        message, context_json, source_report_id, stack_trace,
                        correlation_id, created_at
                    FROM error_logs
                    WHERE correlation_id = $1
                    ORDER BY error_timestamp DESC
                    """,
                    correlation_id,
                )

            result = []
            for row in rows:
                result.append({
                    "id": str(row["id"]),
                    "error_timestamp": row["error_timestamp"],
                    "service_name": row["service_name"],
                    "error_type": row["error_type"],
                    "severity": row["severity"],
                    "message": row["message"],
                    "context_json": row["context_json"],
                    "source_report_id": str(row["source_report_id"]) if row["source_report_id"] else None,
                    "stack_trace": row["stack_trace"],
                    "correlation_id": row["correlation_id"],
                    "created_at": row["created_at"],
                })

            return result

        except Exception as e:
            logger.error(f"Failed to retrieve errors by correlation ID: {str(e)}")
            raise DatabaseError(
                f"Failed to retrieve errors: {str(e)}",
                context={"correlation_id": correlation_id, "error": str(e)},
            )
