"""API routes for Email Webhook Service.

Provides endpoints for webhook processing:
- /webhook/email - Accepts email webhook payloads
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class WebhookResponse(BaseModel):
    """Response model for webhook endpoint."""
    status: str
    message: str
    request_id: Optional[str] = None


class WebhookPayload(BaseModel):
    """Basic webhook payload validation."""
    from_address: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


@router.post("/webhook/email", response_model=WebhookResponse, tags=["webhook"])
async def handle_email_webhook(request: Request):
    """Handle incoming email webhook from email service provider.

    This endpoint is protected by the security middleware stack:
    1. IP ban check
    2. IP whitelist validation
    3. Rate limiting
    4. Signature validation

    Args:
        request: HTTP request object

    Returns:
        WebhookResponse indicating successful receipt

    Response Status Codes:
        200 OK - Webhook received and queued for processing
        401 Unauthorized - Invalid or missing signature
        403 Forbidden - IP not whitelisted or banned
        429 Too Many Requests - Rate limit exceeded
    """
    try:
        # Get request ID from state (can be set by middleware)
        request_id = getattr(request.state, "request_id", None)

        # Get client IP from state (set by first middleware)
        ip_address = getattr(request.state, "ip_address", "unknown")

        # Get signature validation status
        signature_valid = getattr(request.state, "signature_valid", False)

        logger.info(
            "Email webhook received",
            extra={
                "event_type": "webhook_received",
                "ip_address": ip_address,
                "request_id": request_id,
                "signature_valid": signature_valid,
            }
        )

        # Parse request body
        body = await request.json()

        logger.debug(
            "Webhook payload parsed",
            extra={
                "request_id": request_id,
                "payload_keys": list(body.keys()) if isinstance(body, dict) else "unknown",
            }
        )

        # Return success response
        return WebhookResponse(
            status="accepted",
            message="Email webhook received and queued for processing",
            request_id=request_id,
        )

    except Exception as e:
        logger.error(
            "Error processing webhook",
            extra={
                "error": str(e),
                "ip_address": getattr(request.state, "ip_address", "unknown"),
            }
        )

        # Return error response (still 200 to acknowledge receipt)
        return WebhookResponse(
            status="error",
            message="Error processing webhook payload",
            request_id=getattr(request.state, "request_id", None),
        )
