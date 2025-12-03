"""
Cleanup service for maintaining database retention policies.

Handles deletion of old error logs and health check records according to
configured retention periods.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict

from src.config import get_config
from src.db.connection import get_db_connection
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseError

logger = get_logger(__name__)


class CleanupService:
    """Service for cleaning up old records."""

    def __init__(self):
        """Initialize cleanup service."""
        self.config = get_config()

    async def cleanup_error_logs(self) -> Dict:
        """
        Delete error logs older than ERROR_LOG_RETENTION_DAYS.

        Returns:
            Dictionary with count of deleted records

        Raises:
            DatabaseError: If cleanup fails
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=self.config.error_log_retention_days
            )

            async with get_db_connection() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM error_logs
                    WHERE created_at < $1
                    """,
                    cutoff_date,
                )

            # Parse result to extract count
            deleted_count = int(result.split()[-1]) if result else 0

            logger.info(
                f"Error logs cleanup completed: deleted {deleted_count} records "
                f"older than {self.config.error_log_retention_days} days"
            )

            return {
                "table": "error_logs",
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to cleanup error logs: {str(e)}")
            raise DatabaseError(
                f"Failed to cleanup error logs: {str(e)}",
                context={"error": str(e)},
            )

    async def cleanup_health_checks(self) -> Dict:
        """
        Delete health check records older than HEALTH_CHECK_RETENTION_DAYS.

        Returns:
            Dictionary with count of deleted records

        Raises:
            DatabaseError: If cleanup fails
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=self.config.health_check_retention_days
            )

            async with get_db_connection() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM health_checks
                    WHERE created_at < $1
                    """,
                    cutoff_date,
                )

            # Parse result to extract count
            deleted_count = int(result.split()[-1]) if result else 0

            logger.info(
                f"Health checks cleanup completed: deleted {deleted_count} records "
                f"older than {self.config.health_check_retention_days} days"
            )

            return {
                "table": "health_checks",
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to cleanup health checks: {str(e)}")
            raise DatabaseError(
                f"Failed to cleanup health checks: {str(e)}",
                context={"error": str(e)},
            )

    async def cleanup_all(self) -> Dict:
        """
        Run all cleanup operations.

        Returns:
            Dictionary with results of all cleanup operations
        """
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operations": [],
        }

        try:
            error_logs_result = await self.cleanup_error_logs()
            results["operations"].append(error_logs_result)
        except Exception as e:
            logger.error(f"Error logs cleanup failed: {str(e)}")
            results["operations"].append({
                "table": "error_logs",
                "status": "failed",
                "error": str(e),
            })

        try:
            health_checks_result = await self.cleanup_health_checks()
            results["operations"].append(health_checks_result)
        except Exception as e:
            logger.error(f"Health checks cleanup failed: {str(e)}")
            results["operations"].append({
                "table": "health_checks",
                "status": "failed",
                "error": str(e),
            })

        return results
