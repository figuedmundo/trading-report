"""
Structured logging with context support.

Provides get_logger() function for consistent JSON logging across the service.
"""

import logging
import json
import os
from typing import Any


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def __init__(self, service_name: str = "notification-service"):
        """Initialize formatter."""
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "notification_id"):
            log_obj["notification_id"] = record.notification_id
        if hasattr(record, "channel"):
            log_obj["channel"] = record.channel
        if hasattr(record, "recipient"):
            log_obj["recipient"] = record.recipient
        if hasattr(record, "error_code"):
            log_obj["error_code"] = record.error_code
        if hasattr(record, "latency_ms"):
            log_obj["latency_ms"] = record.latency_ms
        if hasattr(record, "retry_count"):
            log_obj["retry_count"] = record.retry_count
        if hasattr(record, "report_id"):
            log_obj["report_id"] = record.report_id
        if hasattr(record, "analysis_id"):
            log_obj["analysis_id"] = record.analysis_id

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
        formatter = JSONFormatter(service_name="notification-service")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Set log level from environment or default to INFO
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))

    return logger
