"""Telegram alerting for security events.

Sends alerts for suspicious patterns with debouncing to prevent spam.
Integrates with the notification service API.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import OrderedDict
from src.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TelegramAlerter:
    """Sends Telegram alerts with debouncing for security events."""

    def __init__(self):
        """Initialize Telegram alerter."""
        self.config = get_config()
        # Track last alert time per pattern: {alert_key: last_sent_timestamp}
        self.alert_debounce: OrderedDict[str, float] = OrderedDict()

    def _should_send_alert(self, alert_key: str) -> bool:
        """
        Check if an alert should be sent based on debounce window.

        Args:
            alert_key: Unique key for the alert pattern

        Returns:
            True if alert should be sent, False if debounced
        """
        if not self.config.security_alert_telegram:
            return False

        now = datetime.utcnow().timestamp()
        debounce_seconds = self.config.security_alert_debounce_minutes * 60

        if alert_key in self.alert_debounce:
            last_sent = self.alert_debounce[alert_key]
            if now - last_sent < debounce_seconds:
                logger.debug(
                    f"Alert debounced",
                    extra={
                        "alert_key": alert_key,
                        "seconds_until_next": int(debounce_seconds - (now - last_sent)),
                    }
                )
                return False

        # Update debounce timestamp
        self.alert_debounce[alert_key] = now

        # Clean up old entries to prevent memory growth
        cutoff_time = now - (debounce_seconds * 2)
        expired_keys = [k for k, v in self.alert_debounce.items() if v < cutoff_time]
        for key in expired_keys:
            del self.alert_debounce[key]

        return True

    async def send_alert(
        self,
        alert_type: str,
        ip_address: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send a Telegram alert for a security event.

        Alert types:
        - ip_banned: IP was automatically banned
        - high_frequency_attack: Many failures from single IP
        - suspicious_pattern: Pattern detected

        Args:
            alert_type: Type of alert
            ip_address: IP address involved
            metadata: Additional alert metadata

        Returns:
            True if alert sent, False if debounced or disabled
        """
        if not self.config.security_alert_telegram:
            logger.debug(
                f"Telegram alerts disabled",
                extra={"alert_type": alert_type, "ip_address": ip_address}
            )
            return False

        metadata = metadata or {}
        alert_key = f"{alert_type}:{ip_address}"

        # Check debouncing
        if not self._should_send_alert(alert_key):
            return False

        # Format alert message
        alert_message = self._format_alert_message(alert_type, ip_address, metadata)

        try:
            # Call notification service API
            # Note: In actual implementation, this would call the notification service
            # For now, we log the alert
            logger.info(
                f"Sending security alert to Telegram",
                extra={
                    "alert_type": alert_type,
                    "ip_address": ip_address,
                    "message": alert_message,
                }
            )

            # TODO: Call notification service API
            # response = await self._call_notification_service(alert_message)
            # if not response.success:
            #     raise Exception(f"Failed to send Telegram alert: {response.error}")

            return True

        except Exception as e:
            # Graceful degradation: log error but don't fail request processing
            logger.warning(
                f"Failed to send Telegram alert",
                extra={
                    "alert_type": alert_type,
                    "ip_address": ip_address,
                    "error": str(e),
                }
            )
            return False

    def _format_alert_message(
        self,
        alert_type: str,
        ip_address: str,
        metadata: Dict[str, Any],
    ) -> str:
        """
        Format alert message for Telegram.

        Args:
            alert_type: Type of alert
            ip_address: IP address
            metadata: Additional metadata

        Returns:
            Formatted alert message
        """
        timestamp = datetime.utcnow().isoformat()

        if alert_type == "ip_banned":
            attempt_count = metadata.get("attempt_count", 0)
            ban_duration = metadata.get("ban_duration_hours", 1)
            return (
                f"SECURITY ALERT: IP Banned\n"
                f"IP: {ip_address}\n"
                f"Failed Attempts: {attempt_count}\n"
                f"Ban Duration: {ban_duration} hour(s)\n"
                f"Time: {timestamp}"
            )

        elif alert_type == "high_frequency_attack":
            event_count = metadata.get("event_count", 0)
            time_window = metadata.get("time_window_minutes", 10)
            return (
                f"SECURITY ALERT: High Frequency Attack Detected\n"
                f"IP: {ip_address}\n"
                f"Events: {event_count} in {time_window} minutes\n"
                f"Action: Monitor for escalation\n"
                f"Time: {timestamp}"
            )

        elif alert_type == "suspicious_pattern":
            pattern_type = metadata.get("pattern_type", "unknown")
            event_count = metadata.get("event_count", 0)
            return (
                f"SECURITY ALERT: Suspicious Pattern Detected\n"
                f"Pattern: {pattern_type}\n"
                f"IP: {ip_address}\n"
                f"Events: {event_count}\n"
                f"Time: {timestamp}"
            )

        else:
            return (
                f"SECURITY ALERT\n"
                f"Type: {alert_type}\n"
                f"IP: {ip_address}\n"
                f"Time: {timestamp}"
            )

    async def _call_notification_service(self, message: str) -> bool:
        """
        Call the notification service API to send Telegram message.

        Args:
            message: Alert message to send

        Returns:
            True if successful, False otherwise
        """
        try:
            # This would call the notification service API
            # Example: POST to http://localhost:8002/api/v1/notify/telegram
            # with payload: {"message": message, "chat_id": TELEGRAM_CHAT_ID}
            logger.debug(f"Would call notification service with message: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to call notification service: {str(e)}")
            return False

    def cleanup_old_debounce_entries(self) -> None:
        """Cleanup old debounce entries to prevent memory growth."""
        now = datetime.utcnow().timestamp()
        debounce_seconds = self.config.security_alert_debounce_minutes * 60
        cutoff_time = now - (debounce_seconds * 2)

        expired_keys = [k for k, v in self.alert_debounce.items() if v < cutoff_time]
        for key in expired_keys:
            del self.alert_debounce[key]

        if expired_keys:
            logger.debug(
                f"Cleaned up old debounce entries",
                extra={"count": len(expired_keys)}
            )
