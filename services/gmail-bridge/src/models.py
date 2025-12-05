"""Pydantic models for Gmail Bridge service."""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class EmailData(BaseModel):
    """Parsed email data structure."""

    subject: str
    from_address: str = Field(alias="from")
    to_address: str = Field(alias="to")
    date: str
    body: str
    report_url: Optional[str] = None

    class Config:
        populate_by_name = True


class WebhookPayload(BaseModel):
    """Payload sent to webhook."""

    from_email: str
    subject: str
    body: str
    report_url: str
    received_at: datetime
    source: str = "gmail-bridge"

    class Config:
        json_schema_extra = {
            "example": {
                "from_email": "sender@example.com",
                "subject": "Trading Report - BTC/USD",
                "body": "Report content here...",
                "report_url": "https://example.com/report/123",
                "received_at": "2025-12-04T13:00:00Z",
                "source": "gmail-bridge",
            }
        }


class HealthStatus(BaseModel):
    """Service health status."""

    status: str = Field(..., description="overall status: ok or error")
    service: str = "gmail-bridge"
    version: str = "0.1.0"
    imap_connected: bool = Field(..., description="IMAP connection status")
    last_poll: Optional[datetime] = Field(None, description="timestamp of last poll")
    emails_processed: int = Field(0, description="total emails processed")
    next_poll: Optional[datetime] = Field(None, description="timestamp of next scheduled poll")


class PollStats(BaseModel):
    """Statistics from a polling cycle."""

    timestamp: datetime
    messages_found: int
    new_messages: int
    successfully_processed: int
    failed_count: int
    errors: list[str] = Field(default_factory=list)


class ServiceInfo(BaseModel):
    """Service information and statistics."""

    name: str = "gmail-bridge"
    version: str = "0.1.0"
    status: str
    uptime_seconds: int
    total_emails_processed: int
    total_errors: int
    poll_interval_seconds: int
    imap_host: str
    webhook_configured: bool
    last_poll_timestamp: Optional[datetime] = None
    next_poll_timestamp: Optional[datetime] = None
