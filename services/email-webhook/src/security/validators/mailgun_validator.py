"""Mailgun-specific signature validation.

Validates requests from Mailgun using their signature format:
- Extract timestamp, token, and signature from X-Mailgun-Signature header
- Verify HMAC-SHA256(timestamp + token, WEBHOOK_SECRET_KEY) == signature
- Validate timestamp freshness (reject if >5 minutes old)
"""

import hmac
import hashlib
import time
from typing import Optional
from src.utils.exceptions import SignatureValidationError
from src.utils.logger import get_logger
from src.config import get_config

logger = get_logger(__name__)


def validate(request_headers: dict, body: bytes) -> bool:
    """Validate Mailgun request signature.

    Args:
        request_headers: Dictionary of request headers (with lowercase keys)
        body: Raw request body bytes

    Returns:
        True if signature is valid, False otherwise

    Raises:
        SignatureValidationError: If signature validation fails
    """
    config = get_config()

    # Extract signature header (normalized to lowercase)
    signature_header = request_headers.get("x-mailgun-signature", "")
    if not signature_header:
        raise SignatureValidationError(
            "Missing X-Mailgun-Signature header",
            context={"provider": "mailgun", "reason": "missing_header"}
        )

    # Parse signature header format: timestamp=<timestamp> token=<token> signature=<signature>
    try:
        parts = {}
        for part in signature_header.split():
            if "=" in part:
                key, value = part.split("=", 1)
                parts[key] = value

        timestamp = parts.get("timestamp")
        token = parts.get("token")
        signature = parts.get("signature")

        if not all([timestamp, token, signature]):
            raise SignatureValidationError(
                "Invalid X-Mailgun-Signature format",
                context={"provider": "mailgun", "reason": "invalid_format"}
            )
    except (ValueError, KeyError) as e:
        raise SignatureValidationError(
            "Failed to parse X-Mailgun-Signature header",
            context={"provider": "mailgun", "reason": "parse_error", "error": str(e)}
        )

    # Validate timestamp freshness (reject if >5 minutes old)
    try:
        timestamp_int = int(timestamp)
        current_time = int(time.time())
        age_seconds = current_time - timestamp_int

        # Mailgun timestamps should be recent (allow 5 minute window for clock skew)
        if age_seconds > 300 or age_seconds < -60:
            raise SignatureValidationError(
                "Timestamp is too old or in the future",
                context={
                    "provider": "mailgun",
                    "reason": "stale_timestamp",
                    "age_seconds": age_seconds
                }
            )
    except ValueError as e:
        raise SignatureValidationError(
            "Invalid timestamp format",
            context={"provider": "mailgun", "reason": "invalid_timestamp", "error": str(e)}
        )

    # Compute expected signature: HMAC-SHA256(timestamp + token, WEBHOOK_SECRET_KEY)
    try:
        message = timestamp + token
        expected_signature = hmac.new(
            config.webhook_secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # Compare signatures using constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(
                "Mailgun signature verification failed",
                extra={
                    "ip_address": request_headers.get("x-forwarded-for", "unknown"),
                    "event_type": "signature_validation_failed",
                    "provider": "mailgun"
                }
            )
            raise SignatureValidationError(
                "Invalid signature",
                context={"provider": "mailgun", "reason": "signature_mismatch"}
            )

    except SignatureValidationError:
        raise
    except Exception as e:
        raise SignatureValidationError(
            "Signature verification failed",
            context={"provider": "mailgun", "reason": "verification_error", "error": str(e)}
        )

    logger.debug(
        "Mailgun signature validated successfully",
        extra={
            "ip_address": request_headers.get("x-forwarded-for", "unknown"),
            "provider": "mailgun"
        }
    )

    return True
