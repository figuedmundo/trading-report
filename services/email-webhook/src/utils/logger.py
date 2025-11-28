"""Structured logging with security context support.

Provides get_logger() function for consistent JSON logging across the service
with security-specific fields like IP address, event type, endpoint, and request ID.
"""

import logging
import json
from typing import Any, Optional
from src.config import get_config


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs with security fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with security context."""
        log_obj = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "service": "email-webhook",
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add security-specific fields from record
        if hasattr(record, "ip_address"):
            log_obj["ip_address"] = record.ip_address
        if hasattr(record, "event_type"):
            log_obj["event_type"] = record.event_type
        if hasattr(record, "endpoint"):
            log_obj["endpoint"] = record.endpoint
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id

        # Add other context fields
        if hasattr(record, "error_code"):
            log_obj["error_code"] = record.error_code
        if hasattr(record, "context"):
            log_obj["context"] = record.context

        return json.dumps(log_obj)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance with JSON formatting and security fields.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance with JSON formatter
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Set log level from config or default to INFO
        try:
            config = get_config()
            log_level = getattr(logging, config.log_level.upper(), logging.INFO)
            logger.setLevel(log_level)
        except Exception:
            logger.setLevel(logging.INFO)

    return logger
