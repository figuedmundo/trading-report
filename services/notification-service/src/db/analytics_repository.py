"""
Analytics repository for aggregated statistics.

Provides queries for delivery statistics and performance metrics.
"""

from typing import Dict, Any
from src.db.connection import get_db_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsRepository:
    """Repository for analytics and statistics."""

    @staticmethod
    async def get_delivery_stats(period_days: int = 7) -> Dict[str, Any]:
        """
        Get delivery statistics for a period.

        Args:
            period_days: Number of days to aggregate

        Returns:
            Dict with aggregated statistics
        """
        try:
            async with get_db_connection() as conn:
                # Query overall statistics
                query = """
                    SELECT
                        COUNT(*) as total_notifications,
                        SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as total_sent,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as total_failed,
                        AVG(latency_ms) as avg_latency_ms,
                        MAX(latency_ms) as max_latency_ms
                    FROM notifications_delivery_log
                    WHERE created_at >= NOW() - INTERVAL '1 day' * $1
                """
                overall_stats = await conn.fetchrow(query, period_days)

                # Query per-channel statistics
                channels_query = """
                    SELECT
                        channel,
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        AVG(latency_ms) as avg_latency_ms
                    FROM notifications_delivery_log
                    WHERE created_at >= NOW() - INTERVAL '1 day' * $1
                    GROUP BY channel
                """
                channels_data = await conn.fetch(channels_query, period_days)

                # Query average retries
                retries_query = """
                    SELECT AVG(retry_count) as avg_retries
                    FROM notifications
                    WHERE created_at >= NOW() - INTERVAL '1 day' * $1
                """
                retries_data = await conn.fetchrow(retries_query, period_days)

            # Build response
            by_channel = {}
            if channels_data:
                for row in channels_data:
                    channel = row["channel"]
                    total = row["total"] or 0
                    sent = row["sent"] or 0
                    failed = row["failed"] or 0
                    success_rate = (sent / total * 100) if total > 0 else 0

                    by_channel[channel] = {
                        "total": total,
                        "sent": sent,
                        "failed": failed,
                        "success_rate": round(success_rate, 2),
                        "avg_latency_ms": int(row["avg_latency_ms"] or 0),
                    }

            total_notifications = overall_stats["total_notifications"] or 0
            max_latency = int(overall_stats["max_latency_ms"] or 0)
            avg_retries = float(retries_data["avg_retries"] or 0) if retries_data else 0.0

            return {
                "total_notifications": total_notifications,
                "by_channel": by_channel,
                "avg_retries": round(avg_retries, 2),
                "largest_latency_ms": max_latency,
            }

        except Exception as e:
            logger.error(f"Error getting delivery stats: {str(e)}")
            return {
                "total_notifications": 0,
                "by_channel": {},
                "avg_retries": 0.0,
                "largest_latency_ms": 0,
            }
