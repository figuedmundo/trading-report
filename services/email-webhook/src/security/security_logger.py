"""Security event logging functionality.

Provides methods to log specific security events with structured metadata.
Integrates with SecurityEventsRepository for database persistence.
"""

from typing import Dict, Any, Optional
from src.db.security_events_repository import SecurityEventsRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityLogger:
    """Logger for security-related events."""

    def __init__(self, repository: SecurityEventsRepository):
        """Initialize security logger.

        Args:
            repository: SecurityEventsRepository instance for database access
        """
        self.repository = repository

    async def log_signature_failure(
        self,
        ip_address: str,
        endpoint: str,
        headers: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log signature validation failure.

        Args:
            ip_address: Source IP address
            endpoint: Request endpoint
            headers: Request headers
            metadata: Additional metadata (provider detected, etc.)
        """
        metadata = metadata or {}

        logger.warning(
            f"Signature validation failed",
            extra={
                "event_type": "signature_validation_failed",
                "ip_address": ip_address,
                "endpoint": endpoint,
            }
        )

        try:
            await self.repository.log_event(
                event_type="signature_validation_failed",
                ip_address=ip_address,
                endpoint=endpoint,
                request_headers=headers,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(
                f"Failed to log signature failure event: {str(e)}",
                extra={
                    "ip_address": ip_address,
                    "endpoint": endpoint,
                    "error": str(e),
                }
            )

    async def log_ip_not_whitelisted(
        self,
        ip_address: str,
        endpoint: str,
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log IP not whitelisted event.

        Args:
            ip_address: Source IP address
            endpoint: Request endpoint
            headers: Request headers (optional)
        """
        headers = headers or {}

        logger.warning(
            f"IP not whitelisted",
            extra={
                "event_type": "ip_not_whitelisted",
                "ip_address": ip_address,
                "endpoint": endpoint,
            }
        )

        try:
            await self.repository.log_event(
                event_type="ip_not_whitelisted",
                ip_address=ip_address,
                endpoint=endpoint,
                request_headers=headers,
                metadata={"reason": "IP not in allowlist"},
            )
        except Exception as e:
            logger.error(
                f"Failed to log IP not whitelisted event: {str(e)}",
                extra={
                    "ip_address": ip_address,
                    "endpoint": endpoint,
                    "error": str(e),
                }
            )

    async def log_rate_limit_exceeded(
        self,
        ip_address: str,
        endpoint: str,
        limit_type: str,
        remaining: int = 0,
        reset_timestamp: Optional[float] = None,
    ) -> None:
        """
        Log rate limit exceeded event.

        Args:
            ip_address: Source IP address
            endpoint: Request endpoint
            limit_type: Type of limit exceeded (per_ip_minute, per_ip_hour, global_hour)
            remaining: Remaining quota after limit check
            reset_timestamp: Unix timestamp when limit resets
        """
        logger.warning(
            f"Rate limit exceeded",
            extra={
                "event_type": "rate_limit_exceeded",
                "ip_address": ip_address,
                "endpoint": endpoint,
                "limit_type": limit_type,
            }
        )

        metadata = {
            "limit_type": limit_type,
            "rate_limit_remaining": remaining,
        }

        if reset_timestamp:
            metadata["rate_limit_reset_timestamp"] = reset_timestamp

        try:
            await self.repository.log_event(
                event_type="rate_limit_exceeded",
                ip_address=ip_address,
                endpoint=endpoint,
                request_headers={},
                metadata=metadata,
            )
        except Exception as e:
            logger.error(
                f"Failed to log rate limit exceeded event: {str(e)}",
                extra={
                    "ip_address": ip_address,
                    "endpoint": endpoint,
                    "error": str(e),
                }
            )

    async def log_ip_banned(
        self,
        ip_address: str,
        reason: str,
        attempt_count: int = 0,
        ban_duration_hours: int = 1,
    ) -> None:
        """
        Log IP banned event.

        Args:
            ip_address: Banned IP address
            reason: Reason for ban (too many failures, etc.)
            attempt_count: Number of failed attempts that triggered ban
            ban_duration_hours: Duration of ban in hours
        """
        logger.error(
            f"IP banned",
            extra={
                "event_type": "ip_banned",
                "ip_address": ip_address,
                "reason": reason,
                "attempt_count": attempt_count,
            }
        )

        metadata = {
            "reason": reason,
            "attempt_count": attempt_count,
            "ban_duration_hours": ban_duration_hours,
        }

        try:
            await self.repository.log_event(
                event_type="ip_banned",
                ip_address=ip_address,
                endpoint="/webhook/*",
                request_headers={},
                metadata=metadata,
            )
        except Exception as e:
            logger.error(
                f"Failed to log IP banned event: {str(e)}",
                extra={
                    "ip_address": ip_address,
                    "error": str(e),
                }
            )

    async def log_suspicious_pattern(
        self,
        ip_address: str,
        pattern_type: str,
        event_count: int,
        time_window_minutes: int = 10,
    ) -> None:
        """
        Log suspicious pattern detection.

        Args:
            ip_address: Source IP address
            pattern_type: Type of pattern (high_frequency_attack, etc.)
            event_count: Number of events in time window
            time_window_minutes: Time window for pattern detection
        """
        logger.error(
            f"Suspicious pattern detected",
            extra={
                "event_type": "suspicious_pattern",
                "ip_address": ip_address,
                "pattern_type": pattern_type,
                "event_count": event_count,
            }
        )

        metadata = {
            "pattern_type": pattern_type,
            "event_count": event_count,
            "time_window_minutes": time_window_minutes,
        }

        try:
            await self.repository.log_event(
                event_type="suspicious_pattern",
                ip_address=ip_address,
                endpoint="/webhook/*",
                request_headers={},
                metadata=metadata,
            )
        except Exception as e:
            logger.error(
                f"Failed to log suspicious pattern event: {str(e)}",
                extra={
                    "ip_address": ip_address,
                    "pattern_type": pattern_type,
                    "error": str(e),
                }
            )
