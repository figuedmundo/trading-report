"""Repository for security events database operations.

Handles storing, querying, and managing security event audit logs.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncpg
from src.db.connection import get_db_connection
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseError

logger = get_logger(__name__)


class SecurityEventsRepository:
    """Repository for security event persistence and querying."""

    async def log_event(
        self,
        event_type: str,
        ip_address: str,
        endpoint: str,
        request_headers: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Log a security event to the database asynchronously.

        Args:
            event_type: Type of event (e.g., signature_validation_failed)
            ip_address: Source IP address
            endpoint: Request endpoint path
            request_headers: Request headers dict (filtered for sensitive data)
            metadata: Additional event metadata

        Returns:
            Created event record as dict

        Raises:
            DatabaseError: If insertion fails
        """
        # Filter sensitive headers before logging
        filtered_headers = self._filter_sensitive_headers(request_headers or {})

        logger.debug(
            "Logging security event",
            extra={
                "event_type": event_type,
                "ip_address": ip_address,
                "endpoint": endpoint,
            }
        )

        try:
            async with get_db_connection() as conn:
                query = """
                    INSERT INTO security_events (event_type, ip_address, endpoint, request_headers, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id, event_type, ip_address, endpoint, request_headers, metadata, created_at
                """

                now = datetime.utcnow()

                row = await conn.fetchrow(
                    query,
                    event_type,
                    ip_address,
                    endpoint,
                    filtered_headers,
                    metadata or {},
                    now,
                )

                if not row:
                    raise DatabaseError(
                        "Failed to insert security event",
                        context={"event_type": event_type, "ip_address": ip_address}
                    )

                result = {
                    "id": str(row["id"]),
                    "event_type": row["event_type"],
                    "ip_address": row["ip_address"],
                    "endpoint": row["endpoint"],
                    "request_headers": row["request_headers"],
                    "metadata": row["metadata"],
                    "created_at": row["created_at"].isoformat(),
                }

                logger.debug(
                    "Security event logged successfully",
                    extra={
                        "event_id": result["id"],
                        "event_type": event_type,
                        "ip_address": ip_address,
                    }
                )

                return result

        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                f"Failed to log security event: {str(e)}",
                context={
                    "event_type": event_type,
                    "ip_address": ip_address,
                    "error": str(e)
                }
            )

    async def get_recent_events(
        self,
        ip_address: Optional[str] = None,
        event_type: Optional[str] = None,
        minutes: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Query recent security events for pattern detection.

        Args:
            ip_address: Filter by IP address (optional)
            event_type: Filter by event type (optional)
            minutes: Look back window in minutes

        Returns:
            List of event records

        Raises:
            DatabaseError: If query fails
        """
        try:
            async with get_db_connection() as conn:
                cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

                # Build query dynamically based on filters
                query = "SELECT * FROM security_events WHERE created_at > $1"
                params = [cutoff_time]
                param_count = 2

                if ip_address:
                    query += f" AND ip_address = ${param_count}"
                    params.append(ip_address)
                    param_count += 1

                if event_type:
                    query += f" AND event_type = ${param_count}"
                    params.append(event_type)
                    param_count += 1

                query += " ORDER BY created_at DESC"

                rows = await conn.fetch(query, *params)

                results = [
                    {
                        "id": str(row["id"]),
                        "event_type": row["event_type"],
                        "ip_address": row["ip_address"],
                        "endpoint": row["endpoint"],
                        "request_headers": row["request_headers"],
                        "metadata": row["metadata"],
                        "created_at": row["created_at"].isoformat(),
                    }
                    for row in rows
                ]

                logger.debug(
                    "Retrieved recent security events",
                    extra={
                        "ip_address": ip_address,
                        "event_type": event_type,
                        "count": len(results),
                        "minutes": minutes,
                    }
                )

                return results

        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                f"Failed to query security events: {str(e)}",
                context={
                    "ip_address": ip_address,
                    "event_type": event_type,
                    "error": str(e)
                }
            )

    async def cleanup_old_events(self, retention_days: int = 90) -> int:
        """
        Delete security events older than retention period.

        Args:
            retention_days: Number of days to retain (default 90)

        Returns:
            Number of events deleted

        Raises:
            DatabaseError: If deletion fails
        """
        cutoff_time = datetime.utcnow() - timedelta(days=retention_days)

        logger.info(
            "Cleaning up old security events",
            extra={"retention_days": retention_days, "cutoff_time": cutoff_time.isoformat()}
        )

        try:
            async with get_db_connection() as conn:
                query = "DELETE FROM security_events WHERE created_at < $1"
                result = await conn.execute(query, cutoff_time)

                # Parse result string like "DELETE 5"
                deleted_count = int(result.split()[-1])

                logger.info(
                    "Security events cleanup completed",
                    extra={
                        "deleted_count": deleted_count,
                        "retention_days": retention_days,
                    }
                )

                return deleted_count

        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                f"Failed to cleanup security events: {str(e)}",
                context={"retention_days": retention_days, "error": str(e)}
            )

    @staticmethod
    def _filter_sensitive_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """
        Filter out sensitive header values before logging.

        Only logs header names, not values, for sensitive headers.

        Args:
            headers: Request headers dict

        Returns:
            Filtered headers dict
        """
        sensitive_keys = {"authorization", "x-signature", "x-mailgun-signature", "x-sendgrid-signature"}

        filtered = {}
        for key, value in headers.items():
            if key.lower() in sensitive_keys:
                # Log header name but not value
                filtered[key] = "[REDACTED]"
            else:
                filtered[key] = value

        return filtered
