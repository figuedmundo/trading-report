"""
Retry scheduler for handling failed notifications.

Periodically checks for notifications eligible for retry and processes them.
"""

import asyncio
from datetime import datetime
import time

from src.db.notifications_repository import NotificationsRepository
from src.services.notification_service import NotificationService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RetryScheduler:
    """Scheduler for retrying failed notifications."""

    def __init__(self, notification_service: NotificationService):
        """
        Initialize retry scheduler.

        Args:
            notification_service: NotificationService instance
        """
        self.notification_service = notification_service
        self.is_running = False
        self._task: asyncio.Task = None

    async def start(self) -> asyncio.Task:
        """
        Start retry scheduler background task.

        Returns:
            asyncio.Task for the scheduler
        """
        if self.is_running:
            logger.warning("Retry scheduler already running")
            return self._task

        logger.info("Starting retry scheduler")
        self.is_running = True
        self._task = asyncio.create_task(self._run())
        return self._task

    async def stop(self) -> None:
        """Stop retry scheduler."""
        logger.info("Stopping retry scheduler")
        self.is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        """Main retry scheduler loop."""
        while self.is_running:
            try:
                # Find eligible notifications
                notification_ids = await NotificationsRepository.find_retry_eligible_notifications()

                if notification_ids:
                    logger.info(f"Found {len(notification_ids)} notifications eligible for retry")

                    # Process each notification
                    for notification_id in notification_ids:
                        if not self.is_running:
                            break

                        try:
                            await self._retry_notification(notification_id)
                        except Exception as e:
                            logger.error(f"Error retrying notification {notification_id}: {str(e)}")

                # Sleep before next check (60 seconds)
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                logger.info("Retry scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Retry scheduler error: {str(e)}")
                await asyncio.sleep(10)  # Wait before retry

    async def _retry_notification(self, notification_id: str) -> None:
        """
        Retry a single notification.

        Args:
            notification_id: Notification ID to retry
        """
        try:
            # Get notification
            notification = await NotificationsRepository.get_notification(notification_id)
            if not notification:
                logger.warning(f"Notification not found: {notification_id}")
                return

            # Check max retries
            retry_count = notification.get("retry_count", 0)
            max_retries = notification.get("max_retries", 5)

            if retry_count >= max_retries:
                logger.info(f"Notification {notification_id} exceeded max retries")
                await NotificationsRepository.update_notification_status(
                    notification_id,
                    status="failed",
                )
                return

            logger.info(f"Retrying notification {notification_id}, attempt {retry_count + 1}")

            # TODO: Implement actual retry logic
            # This would involve:
            # 1. Getting the channel
            # 2. Re-rendering template
            # 3. Sending via channel
            # 4. Updating status

        except Exception as e:
            logger.error(f"Error in retry_notification: {str(e)}")
