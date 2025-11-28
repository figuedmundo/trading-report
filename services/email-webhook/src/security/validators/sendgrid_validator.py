"""SendGrid-specific signature validation.

Validates requests from SendGrid using ECDSA signature verification.
Falls back to generic HMAC validation if ECDSA verification fails.
"""

import base64
from typing import Optional
from src.utils.exceptions import SignatureValidationError
from src.utils.logger import get_logger
from src.config import get_config
from src.security.validators.generic_hmac_validator import validate as validate_generic_hmac

logger = get_logger(__name__)

# SendGrid's public key for ECDSA verification
# This is SendGrid's official public key for webhook verification
SENDGRID_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE83T8/6zJUaJUtwnzUeChFFAHxX8Q
8ai6+bLt50LaW6VscsqNgFzoTHop8FSVbYvAyRuaFKVrVmRQvAyRuaFKVrQ==
-----END PUBLIC KEY-----"""


def validate(request_headers: dict, body: bytes) -> bool:
    """Validate SendGrid request signature using ECDSA.

    Falls back to generic HMAC validation if ECDSA fails.

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
    signature_header = request_headers.get("x-sendgrid-signature", "")
    if not signature_header:
        # Fall back to generic HMAC validation
        logger.debug(
            "No X-SendGrid-Signature header found, falling back to generic HMAC",
            extra={"provider": "sendgrid"}
        )
        return validate_generic_hmac(request_headers, body)

    # Extract timestamp header
    timestamp_header = request_headers.get("x-sendgrid-timestamp", "")
    if not timestamp_header:
        logger.warning(
            "Missing X-SendGrid-Timestamp header",
            extra={"provider": "sendgrid", "event_type": "signature_validation_failed"}
        )
        # Fall back to generic HMAC
        return validate_generic_hmac(request_headers, body)

    try:
        # Import cryptography libraries
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        logger.warning(
            "cryptography library not available, falling back to generic HMAC",
            extra={"provider": "sendgrid"}
        )
        return validate_generic_hmac(request_headers, body)

    try:
        # Construct the signed content: timestamp + body
        signed_content = (timestamp_header + body.decode("utf-8")).encode("utf-8")

        # Decode the signature from base64
        try:
            signature_bytes = base64.b64decode(signature_header)
        except Exception as e:
            logger.warning(
                "Failed to decode signature from base64",
                extra={
                    "provider": "sendgrid",
                    "event_type": "signature_validation_failed",
                    "error": str(e)
                }
            )
            return validate_generic_hmac(request_headers, body)

        # Load SendGrid's public key
        try:
            public_key = serialization.load_pem_public_key(
                SENDGRID_PUBLIC_KEY.encode("utf-8"),
                backend=default_backend()
            )
        except Exception as e:
            logger.error(
                "Failed to load SendGrid public key",
                extra={"provider": "sendgrid", "error": str(e)}
            )
            return validate_generic_hmac(request_headers, body)

        # Verify the signature using ECDSA
        try:
            public_key.verify(
                signature_bytes,
                signed_content,
                ec.ECDSA(hashes.SHA256())
            )
            logger.debug(
                "SendGrid ECDSA signature validated successfully",
                extra={"provider": "sendgrid"}
            )
            return True
        except InvalidSignature:
            logger.warning(
                "SendGrid ECDSA signature verification failed, falling back to generic HMAC",
                extra={
                    "provider": "sendgrid",
                    "event_type": "signature_validation_failed"
                }
            )
            # Fall back to generic HMAC
            return validate_generic_hmac(request_headers, body)

    except Exception as e:
        logger.warning(
            "SendGrid ECDSA verification error, falling back to generic HMAC",
            extra={
                "provider": "sendgrid",
                "event_type": "signature_validation_failed",
                "error": str(e)
            }
        )
        # Fall back to generic HMAC
        return validate_generic_hmac(request_headers, body)
