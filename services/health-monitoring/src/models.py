"""
Pydantic models for request and response validation.

Defines all input validation models and output response structures.
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Literal
from datetime import datetime


# Health Check Models

class HealthCheckResponse(BaseModel):
    """Response model for individual service health check."""

    service_name: str
    status: Literal["up", "down", "degraded"]
    check_timestamp: datetime
    check_duration_ms: int
    details: Optional[Dict] = None


class AggregateHealthResponse(BaseModel):
    """Response model for aggregate health status of all services."""

    timestamp: datetime
    overall_status: Literal["healthy", "degraded", "unhealthy"]
    services: List[HealthCheckResponse]


class ErrorLogEntry(BaseModel):
    """Response model for error log entry."""

    id: str
    error_timestamp: datetime
    service_name: str
    error_type: str
    severity: Literal["CRITICAL", "ERROR", "WARNING"]
    message: str
    context_json: Optional[Dict] = None
    source_report_id: Optional[str] = None
    stack_trace: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime


class ErrorLogListResponse(BaseModel):
    """Response model for error log list."""

    timestamp: datetime
    count: int
    errors: List[ErrorLogEntry]


class AlertLogEntry(BaseModel):
    """Response model for alert log entry."""

    id: str
    error_id: str
    alert_timestamp: datetime
    alert_type: str
    recipient: str
    delivery_status: Literal["sent", "failed", "pending"]
    sent_at: Optional[datetime] = None
    delivery_latency_ms: Optional[int] = None
    created_at: datetime


class HealthCheckRequest(BaseModel):
    """Request model for manual health check trigger."""

    service: str

    @field_validator("service")
    @classmethod
    def validate_service(cls, v: str) -> str:
        """Validate service name."""
        valid_services = {
            "email-webhook",
            "playwright-scraper",
            "ai-analyzer",
            "notification-service",
            "n8n",
        }
        if v not in valid_services:
            raise ValueError(
                f"Invalid service: {v}. Valid services: {valid_services}"
            )
        return v


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    error_code: str
    timestamp: datetime
    details: Optional[Dict] = None
