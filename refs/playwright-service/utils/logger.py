import structlog
import logging
import sys

def configure_logger():
    """
    Configure structlog with redaction for sensitive keys.
    """
    
    # Keys to redact
    SENSITIVE_KEYS = {"password", "secret", "token", "credential", "api_key", "access_token"}

    def redacter(logger, log_method, event_dict):
        """
        Processor to redact sensitive keys.
        """
        for key in event_dict.copy():
            if key.lower() in SENSITIVE_KEYS:
                event_dict[key] = "***REDACTED***"
            # Also check nested dictionaries if needed, but keeping it simple for now
        return event_dict

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            redacter,  # Add our redaction processor
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name=None):
    return structlog.get_logger(name)
