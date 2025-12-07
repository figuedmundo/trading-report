"""
Pydantic models for request and response validation.

Defines all input validation models and output response structures.
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# Request Models

class NotificationRequest(BaseModel):
    """Request body for POST /api/v1/notify endpoint."""

    analysis_id: str
    report_id: str
    channels: List[str]
    recipients: Dict[str, str]
    message_type: str = "summary"
    context_data: Optional[Dict[str, Any]] = None

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: List[str]) -> List[str]:
        """Validate channels list."""
        if not v:
            raise ValueError("channels list must not be empty")

        valid_channels = {"email", "telegram", "sms", "slack", "discord", "webhook"}
        for channel in v:
            if channel not in valid_channels:
                raise ValueError(f"Invalid channel: {channel}. Valid: {valid_channels}")

        return v

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, v: Dict[str, str], info) -> Dict[str, str]:
        """Validate recipients dict matches channels."""
        if not v:
            raise ValueError("recipients dict must not be empty")

        # Check all required channels have recipients
        channels = info.data.get("channels", [])
        for channel in channels:
            if channel not in v:
                raise ValueError(f"No recipient provided for channel: {channel}")

        return v

    @field_validator("message_type")
    @classmethod
    def validate_message_type(cls, v: str) -> str:
        """Validate message_type."""
        valid_types = {"summary", "alert", "detailed_report"}
        if v not in valid_types:
            raise ValueError(f"Invalid message_type: {v}. Valid: {valid_types}")
        return v


class NotificationBatchRequest(BaseModel):
    """Request body for POST /api/v1/notify/batch endpoint."""

    notifications: List[NotificationRequest]

    @field_validator("notifications")
    @classmethod
    def validate_notifications(cls, v: List[NotificationRequest]) -> List[NotificationRequest]:
        """Validate notifications list."""
        if not v:
            raise ValueError("notifications list must not be empty")
        return v


# Response Models

class NotificationSuccessResponse(BaseModel):
    """Success response body for notification endpoint."""

    request_id: str
    status: str
    notification_ids: List[str]
    timestamp: datetime
    channels_created: Dict[str, str]
    duration_ms: int


class NotificationErrorResponse(BaseModel):
    """Error response body for notification endpoint."""

    request_id: str
    error: str
    error_code: str
    affected_channels: List[str] = []
    timestamp: datetime


class DeliveryStatusResponse(BaseModel):
    """Response body for GET /api/v1/delivery-status/{id} endpoint."""

    notification_id: str
    analysis_id: str
    channel: str
    recipient: str  # masked in response
    status: str
    sent_at: Optional[datetime] = None
    latency_ms: Optional[int] = None
    external_id: Optional[str] = None
    retry_count: int
    created_at: datetime


class DeliveryStatsResponse(BaseModel):
    """Response body for GET /api/v1/delivery-stats endpoint."""

    period_days: int
    total_notifications: int
    by_channel: Dict[str, Dict]
    avg_retries: float
    largest_latency_ms: int


class ChannelStatusResponse(BaseModel):
    """Response body for GET /api/v1/channels endpoint."""

    channels: List[Dict]
    timestamp: datetime


class HealthCheckResponse(BaseModel):
    """Response body for GET /health endpoint."""

    status: str
    service: str
    version: str
    timestamp: datetime
    channels: Dict[str, str]
    database: str
