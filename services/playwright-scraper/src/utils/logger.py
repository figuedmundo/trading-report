"""
Structured logging with credential redaction.

Provides get_logger() function for consistent JSON logging across the service.
Implements credential redaction processor to sanitize sensitive keys.
"""

import logging
import json
from typing import Any


class CredentialRedactor(logging.Filter):
    """Filter to redact sensitive credential information from logs."""

    SENSITIVE_KEYS = {
        "password",
        "secret",
        "token",
        "credential",
        "api_key",
        "access_token",
        "username",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive fields from log record."""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            for key in self.SENSITIVE_KEYS:
                if key in record.msg.lower():
                    record.msg = self._redact_string(record.msg)

        # Redact args if present
        if hasattr(record, "args") and isinstance(record.args, dict):
            for key in self.SENSITIVE_KEYS:
                if key in record.args:
                    record.args[key] = "[REDACTED]"

        return True

    @staticmethod
    def _redact_string(text: str) -> str:
        """Redact password values from string."""
        import re

        # Match various password patterns and redact values
        patterns = [
            r'(password\s*[=:]\s*)"[^"]*"',
            r"(password\s*[=:]\s*)'[^']*'",
            r"(password\s*[=:]\s*)[^\s,}]+",
        ]
        for pattern in patterns:
            text = re.sub(pattern, r'\1"[REDACTED]"', text, flags=re.IGNORECASE)
        return text


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "service": "playwright-scraper",
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "url"):
            log_obj["url"] = record.url

        return json.dumps(log_obj)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance with redaction and JSON formatting.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = JSONFormatter()
        handler.setFormatter(formatter)

        # Add redaction filter
        redactor = CredentialRedactor()
        handler.addFilter(redactor)
        logger.addFilter(redactor)

        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
