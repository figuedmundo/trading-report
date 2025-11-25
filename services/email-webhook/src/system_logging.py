"""
Structured logging to PostgreSQL system_logs table.

Records all webhook processing events with correlation ID for audit trail.
"""

import logging
import traceback
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from database import get_db_pool

logger = logging.getLogger(__name__)


def log_event(
    log_level: str,
    message: str,
    correlation_id: str,
    event_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    stack_trace: Optional[str] = None,
) -> bool:
    """
    Log event to system_logs table in PostgreSQL.

    Args:
        log_level: Log level (ERROR, WARNING, INFO, DEBUG)
        message: Event message
        correlation_id: UUID for request tracing
        event_type: Event type (webhook_received, signature_verified, etc.)
        metadata: Additional context as JSONB
        stack_trace: Python traceback (if error)

    Returns:
        True if logged successfully, False otherwise
    """
    try:
        pool = get_db_pool()
        if pool is None:
            # Fallback to standard logging if pool not available
            logger.error(f"[{event_type}] {message} (correlation_id: {correlation_id})")
            return False

        conn = pool.getconn()
        try:
            cursor = conn.cursor()
            try:
                insert_sql = """
                    INSERT INTO system_logs (
                        service_name,
                        log_level,
                        message,
                        correlation_id,
                        event_type,
                        stack_trace,
                        metadata,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """

                metadata_json = json.dumps(metadata or {})

                cursor.execute(
                    insert_sql,
                    (
                        "email_webhook",
                        log_level,
                        message,
                        correlation_id,
                        event_type,
                        stack_trace,
                        metadata_json,
                    ),
                )

                conn.commit()
                return True

            except Exception as e:
                conn.rollback()
                logger.error(f"Error inserting log: {e}")
                return False

            finally:
                cursor.close()

        finally:
            pool.putconn(conn)

    except Exception as e:
        logger.error(f"Unexpected error in log_event: {e}")
        return False


def log_webhook_received(correlation_id: str, email_from: str) -> bool:
    """Log webhook received event."""
    return log_event(
        log_level="INFO",
        message="Webhook request received",
        correlation_id=correlation_id,
        event_type="webhook_received",
        metadata={"email_from": email_from},
    )


def log_signature_verified(correlation_id: str, auth_method: str) -> bool:
    """Log signature verification event."""
    return log_event(
        log_level="DEBUG",
        message=f"Request authenticated via {auth_method}",
        correlation_id=correlation_id,
        event_type="signature_verified",
        metadata={"auth_method": auth_method},
    )


def log_email_parsed(correlation_id: str, email_from: str, subject: str) -> bool:
    """Log email parsed event."""
    return log_event(
        log_level="INFO",
        message="Email parsed successfully",
        correlation_id=correlation_id,
        event_type="email_parsed",
        metadata={"email_from": email_from, "subject": subject},
    )


def log_keywords_matched(correlation_id: str, keywords: list) -> bool:
    """Log keywords matched event."""
    return log_event(
        log_level="INFO",
        message=f"Trading keywords detected: {keywords}",
        correlation_id=correlation_id,
        event_type="keywords_matched",
        metadata={"keywords": keywords},
    )


def log_urls_extracted(correlation_id: str, count: int, urls: list) -> bool:
    """Log URL extraction event."""
    return log_event(
        log_level="INFO",
        message=f"Portal URLs extracted: {count}",
        correlation_id=correlation_id,
        event_type="urls_extracted",
        metadata={"count": count, "urls": urls},
    )


def log_report_created(correlation_id: str, report_id: str) -> bool:
    """Log report creation event."""
    return log_event(
        log_level="INFO",
        message=f"New report created with id: {report_id}",
        correlation_id=correlation_id,
        event_type="report_created",
        metadata={"report_id": report_id},
    )


def log_report_duplicate(correlation_id: str, report_id: str) -> bool:
    """Log duplicate report event."""
    return log_event(
        log_level="INFO",
        message=f"Duplicate email, existing report_id: {report_id}",
        correlation_id=correlation_id,
        event_type="report_duplicate",
        metadata={"report_id": report_id},
    )


def log_signature_invalid(correlation_id: str) -> bool:
    """Log signature verification failure."""
    return log_event(
        log_level="WARNING",
        message="Signature verification failed",
        correlation_id=correlation_id,
        event_type="signature_invalid",
    )


def log_malformed_payload(correlation_id: str, error: str) -> bool:
    """Log malformed payload error."""
    return log_event(
        log_level="WARNING",
        message=f"Invalid JSON or missing fields: {error}",
        correlation_id=correlation_id,
        event_type="malformed_payload",
        metadata={"error": error},
    )


def log_rate_limit_exceeded(correlation_id: str, email_from: str, limit_type: str) -> bool:
    """Log rate limit exceeded event."""
    return log_event(
        log_level="WARNING",
        message=f"Rate limit exceeded ({limit_type})",
        correlation_id=correlation_id,
        event_type="rate_limit_exceeded",
        metadata={"email_from": email_from, "limit_type": limit_type},
    )


def log_database_error(correlation_id: str, error: str) -> bool:
    """Log database operation error."""
    return log_event(
        log_level="ERROR",
        message=f"Database operation failed",
        correlation_id=correlation_id,
        event_type="database_error",
        metadata={"error": error},
        stack_trace=traceback.format_exc(),
    )
