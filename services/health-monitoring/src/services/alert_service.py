"""
Alert generation and delivery service with spam prevention.

Implements alert batching algorithm to prevent alert spam while ensuring critical
errors are escalated quickly.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import aiohttp

from src.config import get_config
from src.db.error_repository import ErrorRepository
from src.db.alert_repository import AlertRepository
from src.utils.logger import get_logger
from src.utils.exceptions import AlertGenerationError

logger = get_logger(__name__)


class AlertService:
    """Service for generating and delivering alerts."""

    def __init__(self):
        """Initialize alert service."""
        self.config = get_config()

    async def check_and_generate_alerts(self) -> List[Dict]:
        """
        Check for CRITICAL errors and generate alerts according to batching rules.

        Algorithm:
        1. Query for CRITICAL errors in the last hour
        2. For each unique (service_name, error_type):
           a. Get current alert state
           b. Apply batching rules:
              - If last_alert < 5 minutes ago: skip (already sent recently)
              - If last_alert < 60 minutes ago AND same error_type: increment counter (batch)
              - If last_alert >= 60 minutes ago OR no previous alert: generate new alert
           c. Update alert_state with new values
        3. Return list of alerts to send

        Returns:
            List of alerts to send with error details
        """
        try:
            alerts_to_send = []
            now = datetime.now(timezone.utc)
            cutoff_time = now - timedelta(hours=1)

            # Query for CRITICAL errors in the last hour
            critical_errors = await ErrorRepository.get_recent_errors(
                severity="CRITICAL",
                hours=1,
                limit=1000,
            )

            if not critical_errors:
                logger.debug("No critical errors found")
                return []

            # Group errors by (service_name, error_type)
            error_groups: Dict[tuple, List[Dict]] = {}
            for error in critical_errors:
                key = (error["service_name"], error["error_type"])
                if key not in error_groups:
                    error_groups[key] = []
                error_groups[key].append(error)

            # Process each error group
            for (service_name, error_type), errors in error_groups.items():
                # Get current alert state
                alert_state = await AlertRepository.get_alert_state(
                    service_name, error_type
                )

                # Determine if we should send an alert
                should_send_alert = False
                message = ""

                if not alert_state:
                    # No previous alert, send one
                    should_send_alert = True
                    message = f"New critical error: {error_type}"
                else:
                    last_alert_time = alert_state.get("last_alert_sent_at")
                    suppressed_until = alert_state.get("alert_suppressed_until")

                    # Check if currently suppressed
                    if suppressed_until and now < suppressed_until:
                        logger.debug(
                            f"Alerts suppressed for {service_name}/{error_type} "
                            f"until {suppressed_until}"
                        )
                        continue

                    if not last_alert_time:
                        # No previous alert
                        should_send_alert = True
                        message = f"New critical error: {error_type}"
                    else:
                        time_since_alert = now - last_alert_time
                        minutes_since = time_since_alert.total_seconds() / 60

                        if minutes_since < 5:
                            # Skip - just sent alert
                            logger.debug(
                                f"Alert too recent for {service_name}/{error_type}"
                            )
                            continue
                        elif minutes_since < 60:
                            # Batch errors - don't send new alert yet
                            logger.debug(
                                f"Batching errors for {service_name}/{error_type}"
                            )
                        else:
                            # Resend alert after batching window
                            should_send_alert = True
                            failure_count = alert_state.get(
                                "consecutive_failure_count", 0
                            )
                            message = (
                                f"Recurring critical error (occurred {failure_count} times): "
                                f"{error_type}"
                            )

                # Update alert state
                new_state = {
                    "last_error_timestamp": errors[0]["error_timestamp"],
                    "consecutive_failure_count": len(errors),
                }

                if should_send_alert:
                    new_state["last_alert_sent_at"] = now

                await AlertRepository.upsert_alert_state(
                    service_name, error_type, new_state
                )

                # Generate alert if needed
                if should_send_alert:
                    alert = {
                        "service_name": service_name,
                        "error_type": error_type,
                        "message": message,
                        "error_count": len(errors),
                        "latest_error": errors[0],
                        "errors": errors[:5],  # Include top 5 errors
                        "timestamp": now,
                    }
                    alerts_to_send.append(alert)

                    logger.info(
                        f"Alert generated: service={service_name}, "
                        f"error_type={error_type}, error_count={len(errors)}"
                    )

            return alerts_to_send

        except Exception as e:
            logger.error(f"Failed to check and generate alerts: {str(e)}")
            raise AlertGenerationError(
                f"Failed to generate alerts: {str(e)}",
                context={"error": str(e)},
            )

    async def send_alerts(self, alerts: List[Dict]) -> None:
        """
        Send alerts via notification service.

        Args:
            alerts: List of alerts to send

        Raises:
            AlertGenerationError: If delivery fails
        """
        if not alerts:
            return

        for alert in alerts:
            try:
                # Prepare notification request
                notification_data = {
                    "template_type": "critical_error_alert",
                    "recipient": self.config.alert_email_admin,
                    "context": {
                        "service_name": alert["service_name"],
                        "error_type": alert["error_type"],
                        "error_message": alert["latest_error"]["message"],
                        "timestamp": alert["timestamp"].isoformat(),
                        "consecutive_failures": alert["error_count"],
                        "errors": [
                            {
                                "type": e["error_type"],
                                "message": e["message"],
                                "time": e["error_timestamp"].isoformat(),
                            }
                            for e in alert["errors"]
                        ],
                    },
                }

                # Call notification service
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.config.notification_service_url}/api/v1/notify",
                        json=notification_data,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status in [200, 202]:
                            # Log successful delivery
                            await AlertRepository.log_alert(
                                error_id=alert["latest_error"]["id"],
                                alert_type="critical_error_alert",
                                recipient=self.config.alert_email_admin,
                                delivery_status="sent",
                            )
                            logger.info(
                                f"Alert sent for {alert['service_name']}/"
                                f"{alert['error_type']}"
                            )
                        else:
                            # Log failed delivery
                            await AlertRepository.log_alert(
                                error_id=alert["latest_error"]["id"],
                                alert_type="critical_error_alert",
                                recipient=self.config.alert_email_admin,
                                delivery_status="failed",
                            )
                            logger.error(
                                f"Alert delivery failed: status={response.status}"
                            )

            except Exception as e:
                logger.error(
                    f"Failed to send alert for {alert['service_name']}: {str(e)}"
                )
                # Don't raise - continue with next alert
                try:
                    await AlertRepository.log_alert(
                        error_id=alert["latest_error"]["id"],
                        alert_type="critical_error_alert",
                        recipient=self.config.alert_email_admin,
                        delivery_status="failed",
                    )
                except Exception as log_error:
                    logger.error(f"Failed to log alert failure: {str(log_error)}")
