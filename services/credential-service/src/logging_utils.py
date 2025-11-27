"""
Log sanitization utilities for preventing credential exposure in logs.

Provides functions to redact sensitive fields from log messages before output.
Handles both plain text and JSON-formatted log messages.

Sensitive patterns redacted: password, credential, secret, token, key, api_key, auth, encrypted_data
"""

import re
import json
import logging
from typing import Any, Dict, Union


# Patterns that indicate sensitive fields
SENSITIVE_PATTERNS = [
    'password',
    'credential',
    'secret',
    'token',
    'key',
    'api_key',
    'auth',
    'encrypted_data',
]

# Build regex pattern for field matching (case-insensitive)
SENSITIVE_PATTERN_REGEX = re.compile(
    '|'.join(SENSITIVE_PATTERNS),
    re.IGNORECASE
)

REDACTION_REPLACEMENT = '[REDACTED]'


def sanitize_log_message(message: str) -> str:
    """
    Redact sensitive values from a log message.

    Handles both plain text key=value format and JSON-formatted messages.
    Preserves field names while replacing sensitive values with [REDACTED].

    Examples:
        "password=secret123" -> "password=[REDACTED]"
        '{"password": "secret123"}' -> '{"password": "[REDACTED]"}'

    Args:
        message: Log message (plain text or JSON)

    Returns:
        str: Sanitized message with sensitive values redacted
    """
    if not message:
        return message

    # Try to parse as JSON first
    try:
        data = json.loads(message)
        sanitized = _sanitize_dict(data)
        return json.dumps(sanitized)
    except (json.JSONDecodeError, ValueError):
        # Not JSON, treat as plain text
        pass

    # Plain text sanitization
    return _sanitize_plain_text(message)


def _sanitize_dict(data: Any) -> Any:
    """
    Recursively sanitize a dictionary, redacting sensitive fields.

    Args:
        data: Dictionary or value to sanitize

    Returns:
        Sanitized version of input
    """
    if isinstance(data, dict):
        return {
            key: (
                REDACTION_REPLACEMENT
                if _is_sensitive_field(key)
                else _sanitize_dict(value)
            )
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [_sanitize_dict(item) for item in data]
    else:
        return data


def _sanitize_plain_text(text: str) -> str:
    """
    Sanitize plain text log messages using regex pattern matching.

    Handles patterns like: key=value, key: value, key:value, key = value
    Also handles values that continue until space, bracket, comma, etc.

    Args:
        text: Plain text message

    Returns:
        Sanitized text
    """
    # Pattern: field_name=[value], field_name: value, field_name:value
    # Captures field names containing sensitive patterns
    # Matches values until: space, closing bracket, comma, newline, or end of string
    pattern = r'(' + SENSITIVE_PATTERN_REGEX.pattern + r')(\s*[=:]\s*)([^\s,\}"\'\n]+)'
    return re.sub(
        pattern,
        r'\1\2' + REDACTION_REPLACEMENT,
        text,
        flags=re.IGNORECASE
    )


def _is_sensitive_field(field_name: str) -> bool:
    """
    Check if a field name matches any sensitive patterns.

    Args:
        field_name: Field name to check

    Returns:
        bool: True if field matches sensitive pattern
    """
    return bool(SENSITIVE_PATTERN_REGEX.search(field_name))


class SanitizingHandler(logging.Handler):
    """
    Custom logging handler that sanitizes messages before output.

    Usage:
        handler = SanitizingHandler()
        logger.addHandler(handler)
    """

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record, sanitizing the message first.

        Args:
            record: Log record to emit
        """
        try:
            # Sanitize the message
            if isinstance(record.msg, str):
                record.msg = sanitize_log_message(record.msg)

            # Also sanitize any formatted message
            if record.getMessage():
                sanitized = sanitize_log_message(record.getMessage())
                record.msg = sanitized
                record.args = ()
        except Exception:
            # Don't fail logging on sanitization error
            pass


def setup_sanitized_logging(logger_instance: logging.Logger, handler=None) -> None:
    """
    Configure a logger to use sanitized output.

    Args:
        logger_instance: Logger to configure
        handler: Optional custom handler (defaults to StreamHandler)
    """
    if handler is None:
        handler = logging.StreamHandler()

    # Add sanitizing wrapper if not already a SanitizingHandler
    if not isinstance(handler, SanitizingHandler):
        handler = SanitizingHandler(handler.stream)

    logger_instance.addHandler(handler)


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a dictionary by redacting sensitive fields.

    Public API for sanitizing structured data.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary
    """
    return _sanitize_dict(data)
