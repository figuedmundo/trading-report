"""
Database operations for storing parsed email metadata.

Inserts report records into PostgreSQL with deduplication via email_message_id.
"""

import hashlib
import logging
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from database import get_db_pool

logger = logging.getLogger(__name__)


def insert_report(
    email_from: str,
    email_subject: str,
    email_message_id: str,
    email_received_at: str,
    report_url: Optional[str],
    metadata: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Insert report into PostgreSQL with deduplication.

    Uses email_message_id as UNIQUE constraint. If duplicate is detected,
    returns existing report_id.

    Args:
        email_from: Sender email address
        email_subject: Email subject
        email_message_id: Unique email message ID
        email_received_at: ISO 8601 timestamp
        report_url: Portal URL (may be None)
        metadata: JSONB metadata dictionary

    Returns:
        Tuple of (success, report_id_or_error)
        - On success: (True, report_id)
        - On duplicate: (True, existing_report_id)
        - On error: (False, error_message)
    """
    try:
        pool = get_db_pool()
        if pool is None:
            return False, "Database connection pool not initialized"

        conn = pool.getconn()
        try:
            cursor = conn.cursor()
            try:
                # Try to insert new report
                insert_sql = """
                    INSERT INTO reports (
                        email_from,
                        email_subject,
                        email_message_id,
                        email_received_at,
                        report_url,
                        status,
                        metadata,
                        created_at,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """

                cursor.execute(
                    insert_sql,
                    (
                        email_from,
                        email_subject,
                        email_message_id,
                        email_received_at,
                        report_url,
                        "pending",
                        json.dumps(metadata),
                    ),
                )

                result = cursor.fetchone()
                report_id = str(result[0]) if result else None

                conn.commit()
                logger.info(f"Report created with ID: {report_id}")
                return True, report_id

            except Exception as e:
                conn.rollback()

                # Check if duplicate (UNIQUE constraint violation)
                error_str = str(e).lower()
                if "unique" in error_str or "duplicate" in error_str:
                    logger.debug(f"Duplicate email_message_id: {email_message_id}")
                    # Query for existing report
                    select_sql = "SELECT id FROM reports WHERE email_message_id = %s"
                    cursor.execute(select_sql, (email_message_id,))
                    result = cursor.fetchone()
                    if result:
                        existing_id = str(result[0])
                        logger.info(f"Returning existing report ID: {existing_id}")
                        return True, existing_id

                logger.error(f"Database insert error: {e}")
                return False, f"Database operation failed: {str(e)[:100]}"

            finally:
                cursor.close()

        finally:
            pool.putconn(conn)

    except Exception as e:
        logger.error(f"Unexpected error in insert_report: {e}")
        return False, f"Unexpected error: {str(e)[:100]}"


def calculate_payload_hash(payload_json: str) -> str:
    """
    Calculate SHA256 hash of raw JSON payload for audit trail.

    Args:
        payload_json: Raw JSON payload as string

    Returns:
        SHA256 hash in hex format
    """
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
