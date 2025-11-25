"""
Tests for Phase 1: Project Setup & Core Infrastructure

Tests FastAPI app initialization, health check endpoint, and database configuration.
Focus on critical startup and health check behaviors only.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app
from models import HealthResponse
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


class TestFastAPIInitialization:
    """Test FastAPI app initialization."""

    def test_app_starts_without_errors(self):
        """Test that FastAPI app initializes correctly."""
        assert app is not None
        assert app.title == "Email Webhook Service"
        assert app.version == "0.1.0"

    def test_app_has_health_endpoint(self):
        """Test that health endpoint is registered."""
        routes = [route.path for route in app.routes]
        assert "/health" in routes

    def test_app_title_and_version(self):
        """Test app metadata is set correctly."""
        assert app.title == "Email Webhook Service"
        assert app.version == "0.1.0"


class TestHealthCheckEndpoint:
    """Test GET /health endpoint behavior."""

    def test_health_check_returns_503_when_pool_not_initialized(self, client):
        """Test health check returns 503 when database pool is not initialized."""
        with patch("main.get_db_pool", return_value=None):
            response = client.get("/health")

            assert response.status_code == 503
            data = response.json()
            assert data["database"] == "disconnected"

    def test_health_check_returns_200_with_valid_database(self, client):
        """Test health check returns 200 OK when database is connected."""
        # Mock a valid connection pool and connection
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.execute.return_value = None

        with patch("main.get_db_pool", return_value=mock_pool):
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["database"] == "connected"
            assert "timestamp" in data

    def test_health_check_returns_503_when_database_unavailable(self, client):
        """Test health check returns 503 when database connection fails."""
        # Mock a pool that fails on query
        mock_pool = MagicMock()
        mock_pool.getconn.side_effect = Exception("Connection refused")

        with patch("main.get_db_pool", return_value=mock_pool):
            response = client.get("/health")

            assert response.status_code == 503
            data = response.json()
            assert data["database"] == "disconnected"

    def test_health_check_includes_timestamp(self, client):
        """Test that health check response includes ISO 8601 timestamp."""
        # Mock a valid connection pool
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.execute.return_value = None

        with patch("main.get_db_pool", return_value=mock_pool):
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            timestamp = data["timestamp"]

            # Verify timestamp is ISO 8601 format
            assert "T" in timestamp
            assert timestamp.endswith("Z")

    def test_health_check_response_schema(self, client):
        """Test health check response matches HealthResponse schema."""
        # Mock a valid connection pool
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.execute.return_value = None

        with patch("main.get_db_pool", return_value=mock_pool):
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Validate response matches HealthResponse schema
            assert "status" in data
            assert "timestamp" in data
            assert "database" in data
            assert data["status"] == "ok"
            assert data["database"] in ["connected", "disconnected"]


class TestConfigInitialization:
    """Test configuration loading."""

    def test_config_loads_environment_variables(self):
        """Test that config loads default values when env vars not set."""
        from config import get_config

        config = get_config()

        assert config is not None
        assert config.database_url is not None
        assert config.webhook_signature_secret is not None
        assert len(config.report_keywords) > 0
        assert len(config.trusted_domains) > 0

    def test_config_parses_keywords_list(self):
        """Test that keywords are parsed as list."""
        from config import get_config

        config = get_config()

        assert isinstance(config.report_keywords, list)
        assert len(config.report_keywords) > 0
        # Check default keywords are present
        assert any("trading" in kw.lower() for kw in config.report_keywords)

    def test_config_parses_trusted_domains(self):
        """Test that trusted domains are parsed as list."""
        from config import get_config

        config = get_config()

        assert isinstance(config.trusted_domains, list)
        assert len(config.trusted_domains) > 0
        # Check default domain is present
        assert "protradingskills.com" in config.trusted_domains


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
