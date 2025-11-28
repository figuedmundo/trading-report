"""Pattern detection for suspicious security behavior.

Analyzes recent security events to identify patterns that warrant alerting.
"""

from typing import List, Dict, Any, Optional
from src.db.security_events_repository import SecurityEventsRepository
from src.utils.logger import get_logger
from src.config import get_config

logger = get_logger(__name__)


class PatternDetector:
    """Detector for suspicious security patterns."""

    def __init__(self, repository: SecurityEventsRepository):
        """Initialize pattern detector.

        Args:
            repository: SecurityEventsRepository instance
        """
        self.repository = repository
        self.config = get_config()

    async def detect_suspicious_patterns(
        self,
        ip_address: str,
        time_window_minutes: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Detect suspicious patterns from recent security events.

        Patterns detected:
        - High frequency failures: >50 failed requests from single IP in 10 minutes

        Args:
            ip_address: IP address to analyze
            time_window_minutes: Time window for pattern detection (default 10 min)

        Returns:
            List of detected patterns with metadata
        """
        patterns = []

        try:
            # Get recent failure events for this IP
            recent_failures = await self.repository.get_recent_events(
                ip_address=ip_address,
                event_type=None,  # Get all events
                minutes=time_window_minutes,
            )

            # Count failed authentication attempts (signature failures, IP not whitelisted, rate limits)
            failure_types = {
                "signature_validation_failed",
                "ip_not_whitelisted",
                "rate_limit_exceeded",
            }

            failed_count = sum(
                1 for event in recent_failures
                if event.get("event_type") in failure_types
            )

            # Pattern: High frequency failures (>threshold in time window)
            threshold = self.config.security_alert_threshold
            if failed_count > threshold:
                pattern = {
                    "type": "high_frequency_failures",
                    "severity": "critical",
                    "ip_address": ip_address,
                    "event_count": failed_count,
                    "time_window_minutes": time_window_minutes,
                    "threshold": threshold,
                    "message": f"Detected {failed_count} failures from {ip_address} in {time_window_minutes} minutes (threshold: {threshold})",
                }
                patterns.append(pattern)

                logger.warning(
                    f"High frequency failure pattern detected",
                    extra={
                        "pattern_type": "high_frequency_failures",
                        "ip_address": ip_address,
                        "event_count": failed_count,
                        "threshold": threshold,
                    }
                )

            return patterns

        except Exception as e:
            logger.error(
                f"Failed to detect patterns: {str(e)}",
                extra={
                    "ip_address": ip_address,
                    "error": str(e),
                }
            )
            return []

    async def detect_global_patterns(
        self,
        time_window_minutes: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Detect global suspicious patterns across all IPs.

        Patterns detected:
        - High volume global failures: >100 failed requests across all IPs in 10 minutes

        Args:
            time_window_minutes: Time window for pattern detection

        Returns:
            List of detected global patterns
        """
        patterns = []

        try:
            # Get all recent failure events
            all_recent_events = await self.repository.get_recent_events(
                ip_address=None,
                event_type=None,
                minutes=time_window_minutes,
            )

            failure_types = {
                "signature_validation_failed",
                "ip_not_whitelisted",
                "rate_limit_exceeded",
            }

            global_failure_count = sum(
                1 for event in all_recent_events
                if event.get("event_type") in failure_types
            )

            # Pattern: Global high failure rate (>100 in time window)
            global_threshold = 100
            if global_failure_count > global_threshold:
                pattern = {
                    "type": "global_high_failure_rate",
                    "severity": "critical",
                    "event_count": global_failure_count,
                    "time_window_minutes": time_window_minutes,
                    "threshold": global_threshold,
                    "message": f"Detected {global_failure_count} total failures globally in {time_window_minutes} minutes (threshold: {global_threshold})",
                }
                patterns.append(pattern)

                logger.error(
                    f"Global high failure rate pattern detected",
                    extra={
                        "pattern_type": "global_high_failure_rate",
                        "event_count": global_failure_count,
                        "threshold": global_threshold,
                    }
                )

            return patterns

        except Exception as e:
            logger.error(
                f"Failed to detect global patterns: {str(e)}",
                extra={
                    "error": str(e),
                }
            )
            return []
