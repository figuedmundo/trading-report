"""Generic HMAC-SHA256 signature validation.

Validates requests using standard HMAC-SHA256 signature verification.
Supports multiple header locations: X-Signature or Authorization header.
"""

import hmac
import hashlib
from typing import Optional
from src.utils.exceptions import SignatureValidationError
from src.utils.logger import get_logger
from src.config import get_config

logger = get_logger(__name__)


def validate(request_headers: dict, body: bytes) -> bool:
    """Validate generic HMAC-SHA256 request signature.

    Supports signature in multiple locations:
    1. X-Signature header (raw signature)
    2. Authorization: Bearer <signature> header

    Args:
        request_headers: Dictionary of request headers (with lowercase keys)
        body: Raw request body bytes

    Returns:
        True if signature is valid, False otherwise

    Raises:
        SignatureValidationError: If signature validation fails
    """
    config = get_config()

    # Try to extract signature from multiple sources
    signature = None

    # Try X-Signature header first (normalized to lowercase)
    if "x-signature" in request_headers:
        signature = request_headers.get("x-signature", "")

    # Try Authorization header (normalized to lowercase)
    if not signature and "authorization" in request_headers:
        auth_header = request_headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            signature = auth_header[7:]  # Strip "Bearer " prefix

    # If no signature found, raise error
    if not signature:
        raise SignatureValidationError(
            "Missing signature header (X-Signature or Authorization)",
            context={"provider": "generic", "reason": "missing_signature"}
        )

    # Compute expected signature: HMAC-SHA256(body, WEBHOOK_SECRET_KEY)
    try:
        expected_signature = hmac.new(
            config.webhook_secret_key.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures using constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(
                "Generic HMAC signature verification failed",
                extra={
                    "ip_address": request_headers.get("x-forwarded-for", "unknown"),
                    "event_type": "signature_validation_failed",
                    "provider": "generic"
                }
            )
            raise SignatureValidationError(
                "Invalid signature",
                context={"provider": "generic", "reason": "signature_mismatch"}
            )

    except SignatureValidationError:
        raise
    except Exception as e:
        raise SignatureValidationError(
            "Signature verification failed",
            context={"provider": "generic", "reason": "verification_error", "error": str(e)}
        )

    logger.debug(
        "Generic HMAC signature validated successfully",
        extra={
            "ip_address": request_headers.get("x-forwarded-for", "unknown"),
            "provider": "generic"
        }
    )

    return True
