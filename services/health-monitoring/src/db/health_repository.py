"""
Health check data access layer.

Handles storage and retrieval of health check results from PostgreSQL.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import uuid
import json

from src.db.connection import get_db_connection
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseError

logger = get_logger(__name__)


class HealthRepository:
    """Repository for health check data operations."""

    @staticmethod
    async def store_health_check(
        service_name: str,
        status: str,
        check_duration_ms: int,
        details: Optional[Dict] = None,
    ) -> str:
        """
        Store health check result to database.

        Args:
            service_name: Name of the service
            status: Health status (up/down/degraded)
            check_duration_ms: Duration of health check in milliseconds
            details: Additional details as dictionary

        Returns:
            UUID of stored health check record

        Raises:
            DatabaseError: If storage fails
        """
        try:
            check_id = str(uuid.uuid4())
            check_timestamp = datetime.now(timezone.utc)

            async with get_db_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO health_checks
                    (id, service_name, status, check_timestamp, check_duration_ms, details_json, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
                    """,
                    check_id,
                    service_name,
                    status,
                    check_timestamp,
                    check_duration_ms,
                    json.dumps(details or {}),
                    check_timestamp,
                )

            logger.info(
                f"Health check stored: service={service_name}, status={status}, duration_ms={check_duration_ms}"
            )
            return check_id

        except Exception as e:
            logger.error(f"Failed to store health check: {str(e)}")
            raise DatabaseError(
                f"Failed to store health check: {str(e)}",
                context={
                    "service_name": service_name,
                    "error": str(e),
                },
            )

    @staticmethod
    async def get_latest_health_checks() -> List[Dict]:
        """
        Get the latest health check for each service.

        Returns:
            List of health check records

        Raises:
            DatabaseError: If retrieval fails
        """
        try:
            async with get_db_connection() as conn:
                # Get latest check per service
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT ON (service_name)
                        id, service_name, status, check_timestamp,
                        check_duration_ms, details_json, created_at
                    FROM health_checks
                    ORDER BY service_name, check_timestamp DESC
                    """
                )

            result = []
            for row in rows:
                result.append({
                    "id": str(row["id"]),
                    "service_name": row["service_name"],
                    "status": row["status"],
                    "check_timestamp": row["check_timestamp"],
                    "check_duration_ms": row["check_duration_ms"],
                    "details": row["details_json"],
                    "created_at": row["created_at"],
                })

            return result

        except Exception as e:
            logger.error(f"Failed to retrieve latest health checks: {str(e)}")
            raise DatabaseError(
                f"Failed to retrieve latest health checks: {str(e)}",
                context={"error": str(e)},
            )

    @staticmethod
    async def get_health_history(
        service_name: str,
        hours: int = 24,
    ) -> List[Dict]:
        """
        Get health check history for a service within time window.

        Args:
            service_name: Name of the service
            hours: Number of hours to look back

        Returns:
            List of health check records

        Raises:
            DatabaseError: If retrieval fails
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            async with get_db_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        id, service_name, status, check_timestamp,
                        check_duration_ms, details_json, created_at
                    FROM health_checks
                    WHERE service_name = $1 AND check_timestamp >= $2
                    ORDER BY check_timestamp DESC
                    """,
                    service_name,
                    cutoff_time,
                )

            result = []
            for row in rows:
                result.append({
                    "id": str(row["id"]),
                    "service_name": row["service_name"],
                    "status": row["status"],
                    "check_timestamp": row["check_timestamp"],
                    "check_duration_ms": row["check_duration_ms"],
                    "details": row["details_json"],
                    "created_at": row["created_at"],
                })

            return result

        except Exception as e:
            logger.error(
                f"Failed to retrieve health history for {service_name}: {str(e)}"
            )
            raise DatabaseError(
                f"Failed to retrieve health history: {str(e)}",
                context={"service_name": service_name, "error": str(e)},
            )
