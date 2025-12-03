"""
Tests for database operations and connection pooling.

Tests health check storage, error logging, and alert state management.
"""

import pytest
import asyncio
from datetime import datetime, timezone
import uuid

from src.db.connection import init_db_pool, close_db_pool, get_db_pool
from src.db.health_repository import HealthRepository
from src.db.error_repository import ErrorRepository
from src.db.alert_repository import AlertRepository


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_pool():
    """Initialize database pool for testing."""
    pool = await init_db_pool()
    yield pool
    await close_db_pool()


@pytest.mark.asyncio
async def test_db_connection_pool_init(db_pool):
    """Test: connection pool initializes successfully."""
    pool = get_db_pool()
    assert pool is not None


@pytest.mark.asyncio
async def test_health_check_storage(db_pool):
    """Test: storing health check with all required fields."""
    service_name = "test-service"
    status = "up"
    duration_ms = 100
    details = {"response_time": 95}

    check_id = await HealthRepository.store_health_check(
        service_name=service_name,
        status=status,
        check_duration_ms=duration_ms,
        details=details,
    )

    assert check_id is not None
    assert len(check_id) == 36  # UUID format


@pytest.mark.asyncio
async def test_error_logging_with_context(db_pool):
    """Test: error logged with all required fields and context."""
    service_name = "test-service"
    error_type = "test_error"
    severity = "CRITICAL"
    message = "Test error message"
    context = {"request_id": "123", "retry_count": 1}
    correlation_id = str(uuid.uuid4())

    error_id = await ErrorRepository.log_error(
        service_name=service_name,
        error_type=error_type,
        severity=severity,
        message=message,
        context=context,
        correlation_id=correlation_id,
    )

    assert error_id is not None
    assert len(error_id) == 36  # UUID format

    # Verify retrieval
    retrieved = await ErrorRepository.get_error_by_id(error_id)
    assert retrieved is not None
    assert retrieved["service_name"] == service_name
    assert retrieved["severity"] == severity
    assert retrieved["correlation_id"] == correlation_id


@pytest.mark.asyncio
async def test_retrieve_errors_by_severity(db_pool):
    """Test: retrieve errors filtered by severity."""
    # Log multiple errors
    for i in range(3):
        await ErrorRepository.log_error(
            service_name="test-service",
            error_type=f"error_type_{i}",
            severity="ERROR",
            message=f"Error message {i}",
        )

    # Retrieve CRITICAL errors
    critical_errors = await ErrorRepository.get_recent_errors(
        severity="CRITICAL",
        hours=24,
    )

    # Retrieve ERROR severity errors
    error_severity_errors = await ErrorRepository.get_recent_errors(
        severity="ERROR",
        hours=24,
    )

    # Should have at least 3 ERROR severity errors
    assert len(error_severity_errors) >= 3


@pytest.mark.asyncio
async def test_alert_state_management(db_pool):
    """Test: alert state tracking for batching."""
    service_name = "test-service"
    error_type = "test_error"

    # Create alert state
    state_id = await AlertRepository.upsert_alert_state(
        service_name=service_name,
        error_type=error_type,
        data={
            "consecutive_failure_count": 5,
            "last_error_timestamp": datetime.now(timezone.utc),
        },
    )

    assert state_id is not None

    # Retrieve state
    state = await AlertRepository.get_alert_state(service_name, error_type)
    assert state is not None
    assert state["consecutive_failure_count"] == 5


@pytest.mark.asyncio
async def test_alert_logging(db_pool):
    """Test: alert delivery logging."""
    # First, create an error to reference
    error_id = await ErrorRepository.log_error(
        service_name="test-service",
        error_type="test_error",
        severity="CRITICAL",
        message="Test error for alert",
    )

    # Log alert
    alert_id = await AlertRepository.log_alert(
        error_id=error_id,
        alert_type="critical_error_alert",
        recipient="test@example.com",
        delivery_status="sent",
    )

    assert alert_id is not None
    assert len(alert_id) == 36  # UUID format

    # Verify retrieval
    alerts = await AlertRepository.get_recent_alerts(limit=10, hours=24)
    assert len(alerts) > 0
    assert any(a["id"] == alert_id for a in alerts)
