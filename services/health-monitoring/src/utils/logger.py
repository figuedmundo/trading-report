"""
Logging configuration and utilities.

Provides structured logging setup with context fields for debugging and monitoring.
"""

import logging
import json
from typing import Any, Dict, Optional
from src.config import get_config


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    config = get_config()
    logger = logging.getLogger(name)

    if not logger.handlers:
        # Configure logging format
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Set log level from config
    log_level = getattr(logging, config.log_level, logging.INFO)
    logger.setLevel(log_level)

    return logger


class StructuredLogger:
    """Logger with support for structured logging with context fields."""

    def __init__(self, logger: logging.Logger):
        """Initialize structured logger."""
        self.logger = logger

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message with optional context."""
        if extra:
            message = f"{message} {json.dumps(extra)}"
        self.logger.info(message)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log error message with optional context."""
        if extra:
            message = f"{message} {json.dumps(extra)}"
        self.logger.error(message)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message with optional context."""
        if extra:
            message = f"{message} {json.dumps(extra)}"
        self.logger.warning(message)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message with optional context."""
        if extra:
            message = f"{message} {json.dumps(extra)}"
        self.logger.debug(message)
