"""
Notification repository for database operations.

Handles CRUD operations for notifications and delivery logs.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4
from src.db.connection import get_db_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationsRepository:
    """Repository for notification database operations."""

    @staticmethod
    async def create_notification(
        analysis_id: str,
        channel: str,
        recipient: str,
        message_type: str = "summary",
    ) -> str:
        """
        Create a new notification record.

        Args:
            analysis_id: Analysis ID
            channel: Channel name (email, telegram, etc.)
            recipient: Recipient address/ID
            message_type: Message type (summary, alert, detailed_report)

        Returns:
            Notification ID
        """
        notification_id = str(uuid4())

        async with get_db_connection() as conn:
            query = """
                INSERT INTO notifications (
                    id, analysis_id, channel, recipient, status,
                    retry_count, max_retries, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """
            await conn.execute(
                query,
                notification_id,
                analysis_id,
                channel,
                recipient,
                "pending",  # status
                0,  # retry_count
                5,  # max_retries
                datetime.utcnow(),
                datetime.utcnow(),
            )

        return notification_id

    @staticmethod
    async def update_notification_status(
        notification_id: str,
        status: str,
        sent_at: Optional[datetime] = None,
        message_id: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
    ) -> None:
        """
        Update notification status.

        Args:
            notification_id: Notification ID
            status: New status (pending, sent, failed, retrying)
            sent_at: When message was sent
            message_id: External message ID
            error_message: Error message if failed
            retry_count: Current retry count
        """
        async with get_db_connection() as conn:
            query = """
                UPDATE notifications
                SET status = $1, sent_at = $2, message_id = $3,
                    error_message = $4, retry_count = $5, updated_at = $6
                WHERE id = $7
            """
            await conn.execute(
                query,
                status,
                sent_at,
                message_id,
                error_message,
                retry_count,
                datetime.utcnow(),
                notification_id,
            )

    @staticmethod
    async def get_notification(notification_id: str) -> Optional[Dict[str, Any]]:
        """
        Get notification by ID.

        Args:
            notification_id: Notification ID

        Returns:
            Notification dict or None
        """
        async with get_db_connection() as conn:
            query = "SELECT * FROM notifications WHERE id = $1"
            row = await conn.fetchrow(query, notification_id)
            return dict(row) if row else None

    @staticmethod
    async def insert_delivery_log(
        notification_id: str,
        attempt_number: int,
        channel: str,
        recipient: str,
        status: str,
        sent_at: Optional[datetime] = None,
        latency_ms: Optional[int] = None,
        external_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_after_seconds: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        Insert delivery log entry (append-only).

        Args:
            notification_id: Notification ID
            attempt_number: Attempt number
            channel: Channel name
            recipient: Recipient address
            status: Delivery status (sent, failed, rate_limited)
            sent_at: Send timestamp
            latency_ms: Delivery latency
            external_id: External message ID
            error_code: Error code if failed
            error_message: Error message if failed
            retry_after_seconds: Retry after seconds (for rate limiting)
            metadata: Additional metadata
        """
        import json

        log_id = str(uuid4())
        metadata_json = json.dumps(metadata or {})

        async with get_db_connection() as conn:
            query = """
                INSERT INTO notifications_delivery_log (
                    id, notification_id, attempt_number, channel, recipient,
                    status, sent_at, latency_ms, external_id, error_code,
                    error_message, retry_after_seconds, metadata, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """
            await conn.execute(
                query,
                log_id,
                notification_id,
                attempt_number,
                channel,
                recipient,
                status,
                sent_at,
                latency_ms,
                external_id,
                error_code,
                error_message,
                retry_after_seconds,
                metadata_json,
                datetime.utcnow(),
            )

    @staticmethod
    async def find_retry_eligible_notifications() -> List[str]:
        """
        Find notifications eligible for retry.

        Returns:
            List of notification IDs to retry
        """
        async with get_db_connection() as conn:
            query = """
                SELECT id
                FROM notifications
                WHERE status = 'retrying'
                  AND retry_count < max_retries
                ORDER BY updated_at ASC
                LIMIT 100
            """
            rows = await conn.fetch(query)
            return [row["id"] for row in rows]
