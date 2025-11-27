"""System logging integration for content extraction."""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def log_extraction_event(
    correlation_id: str,
    report_id: str,
    log_level: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    stack_trace: Optional[str] = None,
    db_pool=None
) -> bool:
    """
    Log extraction event to system_logs table.

    Args:
        correlation_id: Request correlation ID
        report_id: Report ID
        log_level: Log level (INFO, WARNING, ERROR, DEBUG)
        message: Event message
        metadata: Additional context as dict
        stack_trace: Python traceback for errors
        db_pool: Database connection pool

    Returns:
        True if logged successfully, False otherwise
    """
    # Always log to standard logging
    level_func = getattr(logger, log_level.lower(), logger.info)
    level_func(f"[{report_id}] {message}", extra=metadata or {})

    # Try to log to database if pool is available
    if db_pool is None:
        return False

    try:
        conn = db_pool.getconn()
        try:
            cursor = conn.cursor()
            try:
                insert_sql = """
                    INSERT INTO system_logs (
                        service_name,
                        log_level,
                        message,
                        report_id,
                        correlation_id,
                        metadata,
                        stack_trace,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """

                metadata_json = json.dumps(metadata or {})

                cursor.execute(
                    insert_sql,
                    (
                        "content_extraction",
                        log_level,
                        message,
                        report_id,
                        correlation_id,
                        metadata_json,
                        stack_trace,
                    ),
                )

                conn.commit()
                return True

            except Exception as e:
                conn.rollback()
                logger.error(f"Error inserting extraction log: {e}")
                return False

            finally:
                cursor.close()

        finally:
            db_pool.putconn(conn)

    except Exception as e:
        logger.error(f"Unexpected error in log_extraction_event: {e}")
        return False


def log_extraction_started(
    correlation_id: str,
    report_id: str,
    content_size: int,
    db_pool=None
) -> bool:
    """Log extraction started event."""
    return log_extraction_event(
        correlation_id=correlation_id,
        report_id=report_id,
        log_level="DEBUG",
        message="Content extraction started",
        metadata={"content_size_bytes": content_size},
        db_pool=db_pool
    )


def log_extraction_completed(
    correlation_id: str,
    report_id: str,
    duration_ms: int,
    images_found: int,
    images_downloaded: int,
    images_failed: int,
    tradingview_images: int,
    content_length_bytes: int,
    author_extracted: bool,
    date_parsed: bool,
    fallback_used: Optional[str] = None,
    db_pool=None
) -> bool:
    """Log extraction completed event."""
    metadata = {
        "duration_ms": duration_ms,
        "images_found": images_found,
        "images_downloaded": images_downloaded,
        "images_failed": images_failed,
        "tradingview_images": tradingview_images,
        "content_length_bytes": content_length_bytes,
        "author_extracted": author_extracted,
        "date_parsed": date_parsed,
    }

    if fallback_used:
        metadata["fallback_used"] = fallback_used

    return log_extraction_event(
        correlation_id=correlation_id,
        report_id=report_id,
        log_level="INFO",
        message="Content extraction completed successfully",
        metadata=metadata,
        db_pool=db_pool
    )


def log_extraction_failed(
    correlation_id: str,
    report_id: str,
    error_message: str,
    fallback_used: Optional[str] = None,
    stack_trace: Optional[str] = None,
    db_pool=None
) -> bool:
    """Log extraction failure event."""
    metadata = {
        "error": error_message,
    }

    if fallback_used:
        metadata["fallback_used"] = fallback_used

    return log_extraction_event(
        correlation_id=correlation_id,
        report_id=report_id,
        log_level="ERROR",
        message="Content extraction failed",
        metadata=metadata,
        stack_trace=stack_trace,
        db_pool=db_pool
    )


def log_image_download_started(
    correlation_id: str,
    report_id: str,
    images_to_download: int,
    db_pool=None
) -> bool:
    """Log image download started."""
    return log_extraction_event(
        correlation_id=correlation_id,
        report_id=report_id,
        log_level="DEBUG",
        message="Image downloads started",
        metadata={"images_to_download": images_to_download},
        db_pool=db_pool
    )


def log_metadata_extraction_failed(
    correlation_id: str,
    report_id: str,
    field: str,
    db_pool=None
) -> bool:
    """Log metadata extraction failure (author, date, title)."""
    return log_extraction_event(
        correlation_id=correlation_id,
        report_id=report_id,
        log_level="WARNING",
        message=f"Failed to extract {field}",
        metadata={"field": field},
        db_pool=db_pool
    )
