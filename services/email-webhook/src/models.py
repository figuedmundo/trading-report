"""
Pydantic models for webhook request/response validation.

Defines request models for different email provider formats (Mailgun, SendGrid)
and standardized response models for all endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
import uuid


# Request Models

class MailgunPayload(BaseModel):
    """Mailgun webhook payload format."""
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(..., alias="from")
    subject: str
    stripped_text: Optional[str] = None
    text: Optional[str] = None
    html: Optional[str] = None
    timestamp: str
    message_id: str
    to: Optional[str] = None
    cc: Optional[str] = None
    reply_to: Optional[str] = None


class SendGridPayload(BaseModel):
    """SendGrid webhook payload format."""
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(..., alias="from")
    subject: str
    text: Optional[str] = None
    html: Optional[str] = None
    timestamp: str
    message_id: str
    to: Optional[str] = None
    cc: Optional[str] = None
    reply_to: Optional[str] = None


class WebhookRequest(BaseModel):
    """Generic webhook request - supports multiple provider formats."""
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(..., alias="from")
    subject: str
    text: Optional[str] = None
    html: Optional[str] = None
    stripped_text: Optional[str] = None
    timestamp: str
    message_id: str
    message_id_alias: Optional[str] = Field(None, alias="message_id")
    to: Optional[str] = None
    cc: Optional[str] = None
    reply_to: Optional[str] = None


# Response Models

class WebhookSuccessResponse(BaseModel):
    """Successful webhook response (201 Created or 202 Accepted)."""
    success: bool = True
    status: str = Field(..., pattern="^(created|accepted)$")
    report_id: str
    correlation_id: str
    message: str
    timestamp: str


class WebhookErrorResponse(BaseModel):
    """Error webhook response (400, 401, 429, 500)."""
    success: bool = False
    status: str = Field(..., pattern="^(rejected|failed)$")
    error: str
    correlation_id: str
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., pattern="^ok$")
    timestamp: str
    database: str = Field(..., pattern="^(connected|disconnected)$")
