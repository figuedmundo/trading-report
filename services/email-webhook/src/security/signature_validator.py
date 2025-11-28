"""Signature validator factory with auto-detection.

Automatically detects email provider from request headers and routes to
the appropriate signature validator.
"""

from typing import Optional
from src.utils.logger import get_logger
from src.config import get_config
from src.utils.exceptions import SignatureValidationError

# Import validators
from src.security.validators import mailgun_validator
from src.security.validators import sendgrid_validator
from src.security.validators import generic_hmac_validator

logger = get_logger(__name__)


def detect_provider(request_headers: dict) -> str:
    """Auto-detect email provider from request headers.

    Args:
        request_headers: Dictionary of request headers (keys are normalized to lowercase)

    Returns:
        Provider name: "mailgun", "sendgrid", or "generic"
    """
    # Normalize headers to lowercase for comparison (if not already)
    normalized_headers = {k.lower(): v for k, v in request_headers.items()}

    # Check for Mailgun-specific headers
    if "x-mailgun-signature" in normalized_headers or "x-mailgun-event-data" in normalized_headers:
        return "mailgun"

    # Check for SendGrid-specific headers
    if "x-sendgrid-signature" in normalized_headers or "x-sendgrid-timestamp" in normalized_headers:
        return "sendgrid"

    # Check for generic HMAC signature
    if "x-signature" in normalized_headers or (
        "authorization" in normalized_headers
        and normalized_headers.get("authorization", "").startswith("Bearer ")
    ):
        return "generic"

    # Default to generic if no provider detected
    return "generic"


def validate_signature(request_headers: dict, body: bytes) -> bool:
    """Validate request signature with auto-detection.

    Detects the email provider from request headers and routes to the
    appropriate validator. Falls back to generic HMAC validation if
    provider-specific validation fails.

    Args:
        request_headers: Dictionary of request headers
        body: Raw request body bytes

    Returns:
        True if signature is valid

    Raises:
        SignatureValidationError: If signature validation fails
    """
    config = get_config()

    # Check if signature validation is enabled
    if not config.signature_validation_enabled:
        logger.info(
            "Signature validation disabled via configuration",
            extra={"event_type": "signature_validation_bypassed"}
        )
        return True

    # Normalize headers to lowercase for consistent detection
    normalized_headers = {k.lower(): v for k, v in request_headers.items()}

    # Detect provider
    provider = detect_provider(normalized_headers)
    logger.debug(
        f"Detected webhook provider: {provider}",
        extra={"provider": provider}
    )

    try:
        # Route to appropriate validator
        if provider == "mailgun":
            return mailgun_validator.validate(normalized_headers, body)
        elif provider == "sendgrid":
            return sendgrid_validator.validate(normalized_headers, body)
        else:  # generic
            return generic_hmac_validator.validate(normalized_headers, body)

    except SignatureValidationError as e:
        logger.warning(
            f"Signature validation failed for provider: {provider}",
            extra={
                "provider": provider,
                "event_type": "signature_validation_failed",
                "error_code": e.error_code,
                "context": e.context
            }
        )
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during signature validation",
            extra={
                "provider": provider,
                "event_type": "signature_validation_failed",
                "error": str(e)
            }
        )
        raise SignatureValidationError(
            "Signature validation failed",
            context={"provider": provider, "error": str(e)}
        )
