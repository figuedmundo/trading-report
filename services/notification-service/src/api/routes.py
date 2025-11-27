"""
API route definitions for notification service.

Handles HTTP endpoints for notifications, delivery status, and service health.
"""

from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from uuid import uuid4

from src.models import (
    HealthCheckResponse,
    NotificationRequest,
    NotificationSuccessResponse,
    NotificationErrorResponse,
    DeliveryStatusResponse,
    DeliveryStatsResponse,
    ChannelStatusResponse,
)
from src.db.connection import check_db_health
from src.db.notifications_repository import NotificationsRepository
from src.db.analytics_repository import AnalyticsRepository
from src.utils.logger import get_logger
from src.utils.masking import mask_recipient
from src.utils.exceptions import ValidationError, NotificationError

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns:
        HealthCheckResponse with service and channel status

    Raises:
        HTTPException: 503 if database unreachable
    """
    db_healthy = await check_db_health()

    if not db_healthy:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )

    return HealthCheckResponse(
        status="ok",
        service="unified-notification-service",
        version="0.1.0",
        timestamp=datetime.utcnow(),
        channels={
            "email": "ok",
            "telegram": "ok",
        },
        database="ok",
    )


@router.post("/api/v1/notify", status_code=202)
async def notify(request: Request, notification_request: NotificationRequest) -> NotificationSuccessResponse:
    """
    Send notification to specified channels.

    Args:
        request: FastAPI request
        notification_request: NotificationRequest

    Returns:
        NotificationSuccessResponse with notification IDs and status

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        # Get notification service from app state
        notification_service = request.app.state.notification_service

        # Send notifications
        response = await notification_service.send(notification_request)

        logger.info(f"Notification request processed: {response.request_id}")
        return response

    except ValidationError as e:
        logger.error(f"Validation error: {e.message}")
        request_id = str(uuid4())
        raise HTTPException(
            status_code=400,
            detail={
                "request_id": request_id,
                "error": e.message,
                "error_code": e.error_code,
                "affected_channels": [],
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except NotificationError as e:
        logger.error(f"Notification error: {e.message}")
        request_id = str(uuid4())
        raise HTTPException(
            status_code=500,
            detail={
                "request_id": request_id,
                "error": e.message,
                "error_code": e.error_code,
                "affected_channels": [],
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Unexpected error in notify endpoint: {str(e)}")
        request_id = str(uuid4())
        raise HTTPException(
            status_code=500,
            detail={
                "request_id": request_id,
                "error": str(e),
                "error_code": "INTERNAL_ERROR",
                "affected_channels": [],
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@router.get("/api/v1/delivery-status/{notification_id}")
async def get_delivery_status(notification_id: str) -> DeliveryStatusResponse:
    """
    Get delivery status of a notification.

    Args:
        notification_id: Notification ID

    Returns:
        DeliveryStatusResponse with status details

    Raises:
        HTTPException: 404 if notification not found
    """
    try:
        notification = await NotificationsRepository.get_notification(notification_id)

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        masked_recipient = mask_recipient(
            notification.get("recipient", ""),
            notification.get("channel", "")
        )

        return DeliveryStatusResponse(
            notification_id=notification["id"],
            analysis_id=notification.get("analysis_id", ""),
            channel=notification.get("channel", ""),
            recipient=masked_recipient,
            status=notification.get("status", "unknown"),
            sent_at=notification.get("sent_at"),
            latency_ms=notification.get("latency_ms"),
            external_id=notification.get("message_id"),
            retry_count=notification.get("retry_count", 0),
            created_at=notification.get("created_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting delivery status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get delivery status")


@router.get("/api/v1/delivery-stats")
async def get_delivery_stats(period_days: int = 7) -> DeliveryStatsResponse:
    """
    Get delivery statistics.

    Args:
        period_days: Number of days to aggregate (default 7)

    Returns:
        DeliveryStatsResponse with aggregated statistics
    """
    try:
        stats = await AnalyticsRepository.get_delivery_stats(period_days)

        return DeliveryStatsResponse(
            period_days=period_days,
            total_notifications=stats.get("total_notifications", 0),
            by_channel=stats.get("by_channel", {}),
            avg_retries=stats.get("avg_retries", 0.0),
            largest_latency_ms=stats.get("largest_latency_ms", 0),
        )

    except Exception as e:
        logger.error(f"Error getting delivery stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get delivery statistics")


@router.get("/api/v1/channels")
async def get_channels(request: Request) -> ChannelStatusResponse:
    """
    Get status of all enabled channels.

    Args:
        request: FastAPI request

    Returns:
        ChannelStatusResponse with channel status details
    """
    try:
        channel_factory = request.app.state.channel_factory if hasattr(request.app.state, "channel_factory") else None

        if not channel_factory:
            raise HTTPException(status_code=503, detail="Channel factory not initialized")

        channels = []
        for channel_name, channel in channel_factory.channels.items():
            channels.append(channel.get_channel_status())

        return ChannelStatusResponse(
            channels=channels,
            timestamp=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting channels: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get channels")
