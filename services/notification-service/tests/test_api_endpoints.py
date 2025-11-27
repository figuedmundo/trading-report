"""Tests for API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_check_success(client):
    """Test health check endpoint success."""
    with patch("src.api.routes.check_db_health", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = True
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "unified-notification-service"
        assert data["database"] == "ok"
        assert "channels" in data


def test_health_check_failure(client):
    """Test health check endpoint when database fails."""
    with patch("src.api.routes.check_db_health", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = False
        response = client.get("/health")

        assert response.status_code == 503


def test_notify_endpoint_validation_error(client):
    """Test notify endpoint with invalid request."""
    invalid_request = {
        "analysis_id": "test-123",
        "report_id": "test-456",
        "channels": [],  # Empty channels
        "recipients": {},
    }

    response = client.post("/api/v1/notify", json=invalid_request)

    # Should fail validation
    assert response.status_code >= 400


def test_notify_endpoint_missing_fields(client):
    """Test notify endpoint with missing required fields."""
    incomplete_request = {
        "analysis_id": "test-123",
        # Missing report_id, channels, recipients
    }

    response = client.post("/api/v1/notify", json=incomplete_request)

    assert response.status_code >= 400


def test_delivery_status_not_found(client):
    """Test delivery status endpoint with non-existent notification."""
    with patch("src.api.routes.NotificationsRepository.get_notification", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = client.get("/api/v1/delivery-status/nonexistent-id")

        assert response.status_code == 404


def test_delivery_status_found(client):
    """Test delivery status endpoint with existing notification."""
    notification = {
        "id": "test-notif-123",
        "analysis_id": "test-analysis",
        "channel": "email",
        "recipient": "user@example.com",
        "status": "sent",
        "sent_at": "2025-11-27T14:30:00Z",
        "latency_ms": 1000,
        "message_id": "msg-123",
        "retry_count": 0,
        "created_at": "2025-11-27T14:30:00Z",
    }

    with patch("src.api.routes.NotificationsRepository.get_notification", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = notification
        response = client.get("/api/v1/delivery-status/test-notif-123")

        assert response.status_code == 200
        data = response.json()
        assert data["notification_id"] == "test-notif-123"
        assert "***" in data["recipient"]  # Masked


def test_delivery_stats_endpoint(client):
    """Test delivery stats endpoint."""
    stats = {
        "total_notifications": 100,
        "by_channel": {
            "email": {
                "total": 50,
                "sent": 49,
                "failed": 1,
                "success_rate": 98.0,
                "avg_latency_ms": 5000,
            }
        },
        "avg_retries": 0.5,
        "largest_latency_ms": 15000,
    }

    with patch("src.api.routes.AnalyticsRepository.get_delivery_stats", new_callable=AsyncMock) as mock_stats:
        mock_stats.return_value = stats
        response = client.get("/api/v1/delivery-stats?period_days=7")

        assert response.status_code == 200
        data = response.json()
        assert data["total_notifications"] == 100


def test_channels_endpoint(client):
    """Test channels endpoint."""
    with patch.object(app.state, "channel_factory") as mock_factory:
        mock_channel = MagicMock()
        mock_channel.get_channel_status.return_value = {
            "name": "email",
            "enabled": True,
            "rate_limit": 100,
            "tokens_available": 50,
        }
        mock_factory.channels = {"email": mock_channel}

        response = client.get("/api/v1/channels")

        assert response.status_code == 200
        data = response.json()
        assert "channels" in data
        assert len(data["channels"]) > 0
