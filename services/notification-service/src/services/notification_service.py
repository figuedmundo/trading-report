"""
Notification service orchestration layer.

Coordinates channel instantiation, message rendering, and delivery.
"""

import asyncio
import markdown
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import uuid4
import time

from src.models import NotificationRequest, NotificationSuccessResponse
from src.channels.factory import ChannelFactory
from src.channels.base import Channel
from src.templates.engine import TemplateEngine
from src.db.notifications_repository import NotificationsRepository
from src.db.connection import get_db_connection
from src.utils.logger import get_logger
from src.utils.masking import mask_recipient
from src.utils.exceptions import ValidationError, ChannelError, RateLimitError

logger = get_logger(__name__)


class NotificationService:
    """Notification service for sending notifications via multiple channels."""

    def __init__(
        self,
        channel_factory: ChannelFactory,
        template_engine: TemplateEngine,
    ):
        """
        Initialize notification service.

        Args:
            channel_factory: ChannelFactory instance
            template_engine: TemplateEngine instance
        """
        self.channel_factory = channel_factory
        self.template_engine = template_engine

    async def send(self, request: NotificationRequest) -> NotificationSuccessResponse:
        """
        Send notification to specified channels.

        Args:
            request: NotificationRequest

        Returns:
            NotificationSuccessResponse with notification IDs

        Raises:
            ValidationError: If request validation fails
            ChannelError: If channel delivery fails
        """
        request_id = str(uuid4())
        start_time = time.time()

        logger.info(
            "Sending notifications",
            extra={
                "request_id": request_id,
                "analysis_id": request.analysis_id,
                "report_id": request.report_id,
                "channels": request.channels,
            },
        )

        # Validate request
        if not request.channels:
            raise ValidationError("No channels specified")

        if not request.recipients:
            raise ValidationError("No recipients specified")

        # Build template context from analysis
        try:
            context = await self._build_template_context(request.analysis_id)
        except Exception as e:
            logger.error(f"Failed to build template context: {str(e)}")
            context = {
                "report_title": "Trading Analysis",
                "report_url": "",
                "timestamp": datetime.utcnow(),
                "raw_analysis": "Analysis unavailable",
                "html_analysis": "<p>Analysis unavailable</p>",
            }

        # Override with request context_data if present
        if request.context_data:
            context.update(request.context_data)

        # Create notification records and send via channels
        notification_ids = []
        channels_created = {}

        for channel_name in request.channels:
            try:
                # Create notification record
                recipient = request.recipients.get(channel_name)
                if not recipient:
                    raise ValidationError(f"No recipient for channel: {channel_name}")

                notification_id = await NotificationsRepository.create_notification(
                    analysis_id=request.analysis_id,
                    channel=channel_name,
                    recipient=recipient,
                    message_type=request.message_type,
                )
                notification_ids.append(notification_id)

                # Render template
                try:
                    message = await self._render_message(
                        channel_name,
                        request.message_type,
                        context,
                    )
                except Exception as e:
                    logger.error(f"Template render failed for {channel_name}: {str(e)}")
                    message = context.get("raw_analysis", "Trading report analysis")

                # Get channel and send
                channel = await self.channel_factory.get_channel(channel_name)
                if not channel:
                    raise ChannelError(f"Channel not enabled: {channel_name}")

                # Send via channel
                result = await self._send_via_channel(
                    notification_id,
                    channel,
                    message,
                    recipient,
                    request_id,
                )

                channels_created[channel_name] = "success" if result else "failed"

            except Exception as e:
                logger.error(f"Failed to send via {channel_name}: {str(e)}")
                channels_created[channel_name] = "failed"

        duration_ms = int((time.time() - start_time) * 1000)

        response = NotificationSuccessResponse(
            request_id=request_id,
            status="processing",
            notification_ids=notification_ids,
            timestamp=datetime.utcnow(),
            channels_created=channels_created,
            duration_ms=duration_ms,
        )

        logger.info(
            "Notifications sent",
            extra={
                "request_id": request_id,
                "notification_ids": notification_ids,
                "duration_ms": duration_ms,
            },
        )

        return response

    async def _render_message(
        self,
        channel: str,
        message_type: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Render template for channel.

        Args:
            channel: Channel name
            message_type: Message type (summary, alert, detailed_report)
            context: Template variables

        Returns:
            Rendered message string
        """
        template_path = f"{channel}/{message_type}.jinja2"
        return await self.template_engine.render(template_path, context)

    async def _send_via_channel(
        self,
        notification_id: str,
        channel: Channel,
        message: str,
        recipient: str,
        request_id: str,
    ) -> bool:
        """
        Send message via channel.

        Args:
            notification_id: Notification ID
            channel: Channel instance
            message: Message to send
            recipient: Recipient address
            request_id: Request ID for tracking

        Returns:
            True if sent successfully
        """
        attempt_number = 1

        # Check rate limit
        if not await channel.check_rate_limit():
            retry_after = channel.rate_limiter.get_retry_after_seconds()
            logger.warning(
                "Rate limited",
                extra={
                    "notification_id": notification_id,
                    "channel": channel.name,
                    "retry_after_seconds": retry_after,
                },
            )

            # Update as retrying
            await NotificationsRepository.update_notification_status(
                notification_id,
                status="retrying",
                retry_count=1,
            )

            # Log delivery attempt
            await NotificationsRepository.insert_delivery_log(
                notification_id,
                attempt_number,
                channel.name,
                recipient,
                status="rate_limited",
                retry_after_seconds=retry_after,
            )

            return False

        # Send via channel
        start_time = time.time()
        result = await channel.send(message, recipient)
        latency_ms = int((time.time() - start_time) * 1000)

        masked_recipient = mask_recipient(recipient, channel.name)

        if result.get("success"):
            logger.info(
                "Notification sent",
                extra={
                    "notification_id": notification_id,
                    "channel": channel.name,
                    "recipient": masked_recipient,
                    "latency_ms": latency_ms,
                    "external_id": result.get("external_id"),
                },
            )

            # Update as sent
            await NotificationsRepository.update_notification_status(
                notification_id,
                status="sent",
                sent_at=datetime.utcnow(),
                message_id=result.get("external_id"),
                retry_count=0,
            )

            # Log delivery
            await NotificationsRepository.insert_delivery_log(
                notification_id,
                attempt_number,
                channel.name,
                recipient,
                status="sent",
                sent_at=datetime.utcnow(),
                latency_ms=latency_ms,
                external_id=result.get("external_id"),
            )

            return True
        else:
            logger.error(
                "Notification failed",
                extra={
                    "notification_id": notification_id,
                    "channel": channel.name,
                    "recipient": masked_recipient,
                    "error_code": result.get("error_code"),
                    "error_message": result.get("error_message"),
                    "latency_ms": latency_ms,
                },
            )

            # Update as failed or retrying
            await NotificationsRepository.update_notification_status(
                notification_id,
                status="retrying",
                retry_count=1,
            )

            # Log delivery attempt
            await NotificationsRepository.insert_delivery_log(
                notification_id,
                attempt_number,
                channel.name,
                recipient,
                status="failed",
                latency_ms=latency_ms,
                error_code=result.get("error_code"),
                error_message=result.get("error_message"),
            )

            return False

    async def _build_template_context(self, analysis_id: str) -> Dict[str, Any]:
        """
        Build template context from analysis.

        Args:
            analysis_id: Analysis ID

        Returns:
            Template context dict
        """
        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT *
                    FROM analyses
                    WHERE id = $1
                """
                analysis = await conn.fetchrow(query, analysis_id)

            if analysis:
                analysis_dict = dict(analysis)
                
                # Convert raw markdown to HTML for email rendering
                raw_markdown = analysis_dict.get("raw_analysis_response", "") or ""
                try:
                    html_analysis = markdown.markdown(raw_markdown, extensions=['tables', 'fenced_code'])
                except Exception as e:
                    logger.warning(f"Failed to convert markdown to HTML: {e}")
                    html_analysis = raw_markdown.replace("\n", "<br>")
                
                return {
                    "report_title": analysis_dict.get("title") or "Trading Analysis",
                    "report_id": analysis_dict.get("report_id", ""),
                    "report_url": "",
                    "timestamp": datetime.utcnow(),
                    "ai_provider": analysis_dict.get("ai_provider", ""),
                    "model_used": analysis_dict.get("model_used", "unknown"),
                    "prompt_type": analysis_dict.get("prompt_type", "default"),
                    "raw_analysis": raw_markdown,
                    "html_analysis": html_analysis,
                }
        except Exception as e:
            logger.error(f"Failed to build template context from analysis: {str(e)}")

        # Return default context
        return {
            "report_title": "Trading Analysis",
            "report_id": analysis_id,
            "report_url": "",
            "timestamp": datetime.utcnow(),
            "ai_provider": "",
            "model_used": "unknown",
            "prompt_type": "default",
            "raw_analysis": "Analysis unavailable",
            "html_analysis": "<p>Analysis unavailable</p>",
        }
