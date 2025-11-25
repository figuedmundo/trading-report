"""
Security operations for webhook authentication and signature verification.

Implements HMAC-SHA256 signature verification and API key authentication.
"""

import hmac
import hashlib
import logging
from typing import Tuple
from config import get_config

logger = logging.getLogger(__name__)


def verify_hmac_signature(payload: bytes, signature: str) -> bool:
    """
    Verify HMAC-SHA256 signature of webhook payload.

    Args:
        payload: Request body bytes
        signature: Signature from X-Signature header (hex-encoded)

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        config = get_config()
        secret = config.webhook_signature_secret

        # Compute HMAC-SHA256
        computed_signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed_signature, signature)
    except Exception as e:
        logger.error(f"HMAC verification error: {e}")
        return False


def verify_api_key(api_key: str) -> bool:
    """
    Verify API key for fallback authentication.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        True if API key is valid, False otherwise
    """
    try:
        config = get_config()
        expected_key = config.api_key_fallback

        # If no fallback key configured, API key auth is not available
        if not expected_key:
            return False

        # Constant-time comparison
        return hmac.compare_digest(expected_key, api_key)
    except Exception as e:
        logger.error(f"API key verification error: {e}")
        return False


def authenticate_webhook_request(
    payload: bytes,
    signature_header: str = None,
    api_key_header: str = None
) -> Tuple[bool, str]:
    """
    Authenticate webhook request using signature or API key.

    Tries HMAC-SHA256 signature verification first, then falls back to API key.

    Args:
        payload: Request body bytes
        signature_header: X-Signature header value (optional)
        api_key_header: X-API-Key header value (optional)

    Returns:
        Tuple of (is_authenticated, auth_method)
        auth_method is one of: "signature", "api_key", or "none"
    """
    # Try signature verification first
    if signature_header:
        if verify_hmac_signature(payload, signature_header):
            logger.debug("Request authenticated via HMAC-SHA256 signature")
            return True, "signature"

    # Try API key fallback
    if api_key_header:
        if verify_api_key(api_key_header):
            logger.debug("Request authenticated via API key")
            return True, "api_key"

    logger.warning("Request authentication failed")
    return False, "none"
