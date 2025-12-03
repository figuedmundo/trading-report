"""
Alert state and delivery log data access layer.

Handles alert state management for batching and spam prevention, and alert delivery tracking.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import uuid

from src.db.connection import get_db_connection
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseError

logger = get_logger(__name__)


class AlertRepository:
    """Repository for alert state and delivery log operations."""

    @staticmethod
    async def get_alert_state(
        service_name: str,
        error_type: str,
    ) -> Optional[Dict]:
        """
        Get current alert state for service + error_type combination.

        Args:
            service_name: Service name
            error_type: Error type

        Returns:
            Alert state record or None if not exists

        Raises:
            DatabaseError: If query fails
        """
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        id, service_name, error_type, last_alert_sent_at,
                        consecutive_failure_count, last_error_timestamp,
                        alert_suppressed_until, created_at, updated_at
                    FROM alert_state
                    WHERE service_name = $1 AND error_type = $2
                    """,
                    service_name,
                    error_type,
                )

            if not row:
                return None

            return {
                "id": str(row["id"]),
                "service_name": row["service_name"],
                "error_type": row["error_type"],
                "last_alert_sent_at": row["last_alert_sent_at"],
                "consecutive_failure_count": row["consecutive_failure_count"],
                "last_error_timestamp": row["last_error_timestamp"],
                "alert_suppressed_until": row["alert_suppressed_until"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

        except Exception as e:
            logger.error(f"Failed to get alert state: {str(e)}")
            raise DatabaseError(
                f"Failed to get alert state: {str(e)}",
                context={
                    "service_name": service_name,
                    "error_type": error_type,
                    "error": str(e),
                },
            )

    @staticmethod
    async def upsert_alert_state(
        service_name: str,
        error_type: str,
        data: Dict,
    ) -> str:
        """
        Create or update alert state.

        Args:
            service_name: Service name
            error_type: Error type
            data: Fields to update (last_alert_sent_at, consecutive_failure_count,
                  last_error_timestamp, alert_suppressed_until)

        Returns:
            UUID of alert state record

        Raises:
            DatabaseError: If operation fails
        """
        try:
            state_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            async with get_db_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO alert_state
                    (id, service_name, error_type, last_alert_sent_at,
                     consecutive_failure_count, last_error_timestamp,
                     alert_suppressed_until, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (service_name, error_type)
                    DO UPDATE SET
                        last_alert_sent_at = COALESCE($4, alert_state.last_alert_sent_at),
                        consecutive_failure_count = COALESCE($5, alert_state.consecutive_failure_count),
                        last_error_timestamp = COALESCE($6, alert_state.last_error_timestamp),
                        alert_suppressed_until = COALESCE($7, alert_state.alert_suppressed_until),
                        updated_at = $9
                    """,
                    state_id,
                    service_name,
                    error_type,
                    data.get("last_alert_sent_at"),
                    data.get("consecutive_failure_count"),
                    data.get("last_error_timestamp"),
                    data.get("alert_suppressed_until"),
                    now,
                    now,
                )

            logger.info(
                f"Alert state upserted: service={service_name}, error_type={error_type}"
            )
            return state_id

        except Exception as e:
            logger.error(f"Failed to upsert alert state: {str(e)}")
            raise DatabaseError(
                f"Failed to upsert alert state: {str(e)}",
                context={
                    "service_name": service_name,
                    "error_type": error_type,
                    "error": str(e),
                },
            )

    @staticmethod
    async def log_alert(
        error_id: str,
        alert_type: str,
        recipient: str,
        delivery_status: str,
    ) -> str:
        """
        Log alert generation and delivery.

        Args:
            error_id: ID of error that triggered alert
            alert_type: Type of alert
            recipient: Email recipient
            delivery_status: Delivery status (pending, sent, failed)

        Returns:
            UUID of alert log record

        Raises:
            DatabaseError: If logging fails
        """
        try:
            alert_id = str(uuid.uuid4())
            alert_timestamp = datetime.now(timezone.utc)

            async with get_db_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO alert_logs
                    (id, error_id, alert_timestamp, alert_type, recipient,
                     delivery_status, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    alert_id,
                    error_id,
                    alert_timestamp,
                    alert_type,
                    recipient,
                    delivery_status,
                    alert_timestamp,
                )

            logger.info(
                f"Alert logged: error_id={error_id}, type={alert_type}, "
                f"recipient={recipient}"
            )
            return alert_id

        except Exception as e:
            logger.error(f"Failed to log alert: {str(e)}")
            raise DatabaseError(
                f"Failed to log alert: {str(e)}",
                context={"error_id": error_id, "error": str(e)},
            )

    @staticmethod
    async def update_alert_delivery_status(
        alert_id: str,
        delivery_status: str,
        sent_at: Optional[datetime] = None,
        latency_ms: Optional[int] = None,
    ) -> None:
        """
        Update alert delivery status after sending.

        Args:
            alert_id: UUID of alert log record
            delivery_status: New delivery status
            sent_at: Timestamp when sent
            latency_ms: Delivery latency in milliseconds

        Raises:
            DatabaseError: If update fails
        """
        try:
            async with get_db_connection() as conn:
                await conn.execute(
                    """
                    UPDATE alert_logs
                    SET delivery_status = $1, sent_at = $2, delivery_latency_ms = $3
                    WHERE id = $4
                    """,
                    delivery_status,
                    sent_at,
                    latency_ms,
                    alert_id,
                )

            logger.info(
                f"Alert delivery status updated: alert_id={alert_id}, "
                f"status={delivery_status}"
            )

        except Exception as e:
            logger.error(f"Failed to update alert delivery status: {str(e)}")
            raise DatabaseError(
                f"Failed to update alert delivery status: {str(e)}",
                context={"alert_id": alert_id, "error": str(e)},
            )

    @staticmethod
    async def get_recent_alerts(limit: int = 100, hours: int = 24) -> List[Dict]:
        """
        Retrieve recent alerts.

        Args:
            limit: Maximum number of records to return
            hours: Number of hours to look back

        Returns:
            List of alert log records

        Raises:
            DatabaseError: If retrieval fails
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            async with get_db_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        id, error_id, alert_timestamp, alert_type, recipient,
                        delivery_status, sent_at, delivery_latency_ms, created_at
                    FROM alert_logs
                    WHERE alert_timestamp >= $1
                    ORDER BY alert_timestamp DESC
                    LIMIT $2
                    """,
                    cutoff_time,
                    limit,
                )

            result = []
            for row in rows:
                result.append({
                    "id": str(row["id"]),
                    "error_id": str(row["error_id"]),
                    "alert_timestamp": row["alert_timestamp"],
                    "alert_type": row["alert_type"],
                    "recipient": row["recipient"],
                    "delivery_status": row["delivery_status"],
                    "sent_at": row["sent_at"],
                    "delivery_latency_ms": row["delivery_latency_ms"],
                    "created_at": row["created_at"],
                })

            return result

        except Exception as e:
            logger.error(f"Failed to retrieve recent alerts: {str(e)}")
            raise DatabaseError(
                f"Failed to retrieve recent alerts: {str(e)}",
                context={"error": str(e)},
            )
