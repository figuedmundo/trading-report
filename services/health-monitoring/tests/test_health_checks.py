"""
Tests for health check service logic.

Tests service health checks with mocked HTTP calls and timeout handling.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone

from src.services.health_check_service import HealthCheckService
from src.db.health_repository import HealthRepository


@pytest.fixture
def health_service():
    """Create a health check service instance."""
    return HealthCheckService()


@pytest.mark.asyncio
async def test_email_webhook_health_check_success(health_service):
    """Test: email-webhook service health check with successful response."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        mock_get.return_value.__aenter__.return_value = mock_response

        with patch("aiohttp.ClientSession.__aenter__", return_value=AsyncMock()):
            result = await health_service.check_email_webhook()

        assert result["service_name"] == "email-webhook"
        assert result["status"] == "up"
        assert result["check_duration_ms"] >= 0


@pytest.mark.asyncio
async def test_playwright_scraper_health_check_success(health_service):
    """Test: playwright-scraper service health check with successful response."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        mock_get.return_value.__aenter__.return_value = mock_response

        with patch("aiohttp.ClientSession.__aenter__", return_value=AsyncMock()):
            result = await health_service.check_playwright_scraper()

        assert result["service_name"] == "playwright-scraper"
        assert result["status"] == "up"


@pytest.mark.asyncio
async def test_health_check_timeout_handling(health_service):
    """Test: health check timeout marks service as down."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Simulate timeout
        mock_get.side_effect = asyncio.TimeoutError()

        with patch("aiohttp.ClientSession.__aenter__", return_value=AsyncMock()):
            result = await health_service.check_email_webhook()

        assert result["status"] == "down"
        assert "error" in result["details"]


@pytest.mark.asyncio
async def test_health_check_connection_error(health_service):
    """Test: health check handles connection errors gracefully."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Simulate connection error
        mock_get.side_effect = Exception("Connection refused")

        with patch("aiohttp.ClientSession.__aenter__", return_value=AsyncMock()):
            result = await health_service.check_email_webhook()

        assert result["status"] == "down"
        assert result["details"]["error"] is not None


@pytest.mark.asyncio
async def test_health_check_degraded_status(health_service):
    """Test: health check reports degraded status on non-200 response."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 503  # Service unavailable
        mock_get.return_value.__aenter__.return_value = mock_response

        with patch("aiohttp.ClientSession.__aenter__", return_value=AsyncMock()):
            result = await health_service.check_email_webhook()

        assert result["status"] == "degraded"
        assert result["details"]["http_status"] == 503


@pytest.mark.asyncio
async def test_run_all_checks_returns_list(health_service):
    """Test: run_all_checks returns list of health check results."""
    with patch.object(health_service, "check_email_webhook", new_callable=AsyncMock) as mock1:
        with patch.object(health_service, "check_playwright_scraper", new_callable=AsyncMock) as mock2:
            with patch.object(health_service, "check_ai_analyzer", new_callable=AsyncMock) as mock3:
                with patch.object(health_service, "check_notification_service", new_callable=AsyncMock) as mock4:
                    with patch.object(health_service, "check_n8n", new_callable=AsyncMock) as mock5:
                        # Setup return values
                        mock1.return_value = {
                            "service_name": "email-webhook",
                            "status": "up",
                            "check_timestamp": datetime.now(timezone.utc),
                            "check_duration_ms": 100,
                        }
                        mock2.return_value = {
                            "service_name": "playwright-scraper",
                            "status": "up",
                            "check_timestamp": datetime.now(timezone.utc),
                            "check_duration_ms": 150,
                        }
                        mock3.return_value = {
                            "service_name": "ai-analyzer",
                            "status": "up",
                            "check_timestamp": datetime.now(timezone.utc),
                            "check_duration_ms": 120,
                        }
                        mock4.return_value = {
                            "service_name": "notification-service",
                            "status": "up",
                            "check_timestamp": datetime.now(timezone.utc),
                            "check_duration_ms": 110,
                        }
                        mock5.return_value = {
                            "service_name": "n8n",
                            "status": "up",
                            "check_timestamp": datetime.now(timezone.utc),
                            "check_duration_ms": 200,
                        }

                        results = await health_service.run_all_checks()

        assert len(results) == 5
        assert all(isinstance(r, dict) for r in results)
        assert all("service_name" in r and "status" in r for r in results)
