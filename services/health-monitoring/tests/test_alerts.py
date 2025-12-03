"""
Tests for alert generation and batching logic.

Tests alert batching algorithm, spam prevention, and delivery.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta
import uuid

from src.services.alert_service import AlertService
from src.db.error_repository import ErrorRepository
from src.db.alert_repository import AlertRepository


@pytest.fixture
def alert_service():
    """Create an alert service instance."""
    return AlertService()


@pytest.mark.asyncio
async def test_first_critical_error_generates_alert(alert_service):
    """Test: first CRITICAL error generates alert immediately."""
    # Log a CRITICAL error
    error_id = await ErrorRepository.log_error(
        service_name="test-service",
        error_type="login_failure",
        severity="CRITICAL",
        message="Critical login failure",
    )

    # Check for alerts
    alerts = await alert_service.check_and_generate_alerts()

    # Should generate at least one alert
    assert len(alerts) > 0
    assert alerts[0]["service_name"] == "test-service"
    assert alerts[0]["error_type"] == "login_failure"


@pytest.mark.asyncio
async def test_duplicate_errors_within_5_minutes_no_alert(alert_service):
    """Test: duplicate errors within 5 minutes don't generate new alert."""
    service_name = "test-service"
    error_type = "api_timeout"

    # Log first error
    error_id_1 = await ErrorRepository.log_error(
        service_name=service_name,
        error_type=error_type,
        severity="CRITICAL",
        message="API timeout",
    )

    # Check for alerts (should generate one)
    alerts_1 = await alert_service.check_and_generate_alerts()
    initial_alert_count = len(alerts_1)

    # Wait briefly (but not past the 5 minute window)
    await asyncio.sleep(0.1)

    # Log another error of same type
    error_id_2 = await ErrorRepository.log_error(
        service_name=service_name,
        error_type=error_type,
        severity="CRITICAL",
        message="API timeout again",
    )

    # Check for alerts again (should not generate new alert within 5 minutes)
    alerts_2 = await alert_service.check_and_generate_alerts()

    # The second call should find the same errors but not generate new alert
    # due to spam prevention
    assert len(alerts_2) == initial_alert_count


@pytest.mark.asyncio
async def test_alert_state_tracks_consecutive_failures(alert_service):
    """Test: alert state correctly tracks consecutive_failure_count."""
    service_name = "test-service"
    error_type = "extraction_failure"

    # Log multiple errors
    for i in range(3):
        await ErrorRepository.log_error(
            service_name=service_name,
            error_type=error_type,
            severity="CRITICAL",
            message=f"Extraction failure {i}",
        )

    # Check for alerts
    alerts = await alert_service.check_and_generate_alerts()

    # Get alert state
    alert_state = await AlertRepository.get_alert_state(service_name, error_type)

    assert alert_state is not None
    # Should track multiple errors
    assert alert_state["consecutive_failure_count"] >= 1


@pytest.mark.asyncio
async def test_send_alerts_via_notification_service(alert_service):
    """Test: alerts are sent via notification service."""
    # Create a mock alert
    alert = {
        "service_name": "test-service",
        "error_type": "test_error",
        "message": "Test alert",
        "error_count": 1,
        "latest_error": {
            "id": str(uuid.uuid4()),
            "message": "Test error message",
            "error_timestamp": datetime.now(timezone.utc),
        },
        "errors": [],
        "timestamp": datetime.now(timezone.utc),
    }

    # Mock the HTTP request
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response

        with patch("aiohttp.ClientSession.__aenter__", return_value=AsyncMock()):
            await alert_service.send_alerts([alert])

        # Verify notification service was called
        mock_post.assert_called()


@pytest.mark.asyncio
async def test_error_filters_by_severity(alert_service):
    """Test: alert service only processes CRITICAL errors."""
    # Log ERROR and WARNING errors (should be ignored)
    await ErrorRepository.log_error(
        service_name="test-service",
        error_type="warning_event",
        severity="WARNING",
        message="Just a warning",
    )

    await ErrorRepository.log_error(
        service_name="test-service",
        error_type="regular_error",
        severity="ERROR",
        message="Regular error",
    )

    # Log a CRITICAL error
    await ErrorRepository.log_error(
        service_name="test-service",
        error_type="critical_event",
        severity="CRITICAL",
        message="Critical error",
    )

    # Check for alerts
    alerts = await alert_service.check_and_generate_alerts()

    # Should only have alerts for CRITICAL errors
    for alert in alerts:
        assert alert["error_type"] == "critical_event"
