"""Background cleanup task for rate limits and security events.

Runs periodically (every 60 seconds) to:
1. Remove expired rate limit entries
2. Remove expired IP bans
3. Delete old security events from database

Integrates with FastAPI BackgroundTasks.
"""

import asyncio
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class CleanupTask:
    """Manages periodic cleanup of security data."""

    def __init__(
        self,
        rate_limit_storage: Any = None,
        ban_manager: Any = None,
        db_pool: Optional[Any] = None,
        security_event_retention_days: int = 90,
        cleanup_interval_seconds: int = 60,
    ):
        """Initialize cleanup task.

        Args:
            rate_limit_storage: RateLimitStorage instance to cleanup
            ban_manager: BanManager instance to cleanup
            db_pool: asyncpg connection pool for database cleanup
            security_event_retention_days: Days to retain security events (default 90)
            cleanup_interval_seconds: How often to run cleanup (default 60 seconds)
        """
        self.rate_limit_storage = rate_limit_storage
        self.ban_manager = ban_manager
        self.db_pool = db_pool
        self.security_event_retention_days = security_event_retention_days
        self.cleanup_interval_seconds = cleanup_interval_seconds

    async def run(self) -> None:
        """Run cleanup tasks continuously.

        This should be started as a background task during app startup.
        """
        logger.info("Cleanup task started")

        while True:
            try:
                await self.cleanup_once()
            except Exception as e:
                logger.error(f"Cleanup task failed: {e}", exc_info=True)

            # Sleep before next cleanup
            await asyncio.sleep(self.cleanup_interval_seconds)

    async def cleanup_once(self) -> None:
        """Execute a single cleanup cycle.

        Called by run() every cleanup_interval_seconds.
        Can also be called directly from tests or manual triggers.
        """
        logger.debug("Running cleanup cycle")

        # Cleanup rate limit storage
        if self.rate_limit_storage:
            removed = self.rate_limit_storage.cleanup_expired(ttl_seconds=3600)
            if removed > 0:
                logger.debug(f"Cleaned up {removed} expired rate limit entries")

        # Cleanup IP bans
        if self.ban_manager:
            removed = self.ban_manager.cleanup_expired_bans()
            if removed > 0:
                logger.debug(f"Cleaned up {removed} expired IP bans")

            # Sync bans to database
            try:
                await self.ban_manager.sync_to_database()
            except Exception as e:
                logger.warning(f"Failed to sync bans to database: {e}")

        # Cleanup old security events from database
        if self.db_pool:
            await self._cleanup_old_security_events()

    async def _cleanup_old_security_events(self) -> None:
        """Delete security events older than retention period.

        Removes events from security_events table that are older than
        SECURITY_EVENT_RETENTION_DAYS (default 90 days).
        """
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM security_events
                    WHERE created_at < NOW() - INTERVAL '%d days'
                    """,
                    self.security_event_retention_days
                )

                # Extract number of rows deleted
                # asyncpg returns a string like "DELETE N"
                deleted_count = 0
                if isinstance(result, str):
                    parts = result.split()
                    if len(parts) >= 2:
                        try:
                            deleted_count = int(parts[1])
                        except ValueError:
                            pass

                if deleted_count > 0:
                    logger.debug(f"Deleted {deleted_count} old security events")

        except Exception as e:
            logger.warning(f"Failed to cleanup old security events: {e}")


async def start_cleanup_task(
    rate_limit_storage: Any = None,
    ban_manager: Any = None,
    db_pool: Optional[Any] = None,
    security_event_retention_days: int = 90,
    cleanup_interval_seconds: int = 60,
) -> asyncio.Task:
    """Start the cleanup task as a background task.

    Args:
        rate_limit_storage: RateLimitStorage instance
        ban_manager: BanManager instance
        db_pool: asyncpg connection pool
        security_event_retention_days: Days to retain security events
        cleanup_interval_seconds: Cleanup interval in seconds

    Returns:
        asyncio.Task that can be cancelled on shutdown
    """
    cleanup = CleanupTask(
        rate_limit_storage=rate_limit_storage,
        ban_manager=ban_manager,
        db_pool=db_pool,
        security_event_retention_days=security_event_retention_days,
        cleanup_interval_seconds=cleanup_interval_seconds,
    )

    # Start cleanup as a background task
    task = asyncio.create_task(cleanup.run())
    logger.info("Cleanup task scheduled")

    return task
