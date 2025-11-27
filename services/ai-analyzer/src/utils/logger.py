"""
Structured logging with context support.

Provides get_logger() function for consistent JSON logging across the service.
"""

import logging
import json
from typing import Any


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "service": "ai-analyzer",
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "report_id"):
            log_obj["report_id"] = record.report_id
        if hasattr(record, "provider"):
            log_obj["provider"] = record.provider
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "error_code"):
            log_obj["error_code"] = record.error_code

        return json.dumps(log_obj)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance with JSON formatting.

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
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
