"""Tests for Gmail Bridge FastAPI application."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

# Configure environment before importing the app
import os
os.environ['SMTP_USER'] = 'test@gmail.com'
os.environ['EMAIL_PASSWORD'] = 'test-password'
os.environ['WEBHOOK_URL'] = 'http://localhost:5678/webhook'

from src.main import app
from src.gmail_poller import GmailPoller


@pytest.fixture
def client():
    """Create a TestClient for the FastAPI app."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "gmail-bridge"
    assert "endpoints" in data


def test_health_endpoint(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert data["service"] == "gmail-bridge"


def test_config_endpoint(client):
    """Test config endpoint."""
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "gmail-bridge"
    assert "imap_host" in data
    assert "poll_interval" in data


def test_docs_endpoint(client):
    """Test OpenAPI documentation endpoint."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


def test_api_endpoints_exist(client):
    """Test that all documented API endpoints exist."""
    endpoints = [
        "/",
        "/health",
        "/api/v1/status",
        "/api/v1/config",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code != 404, f"Endpoint {endpoint} should exist"


def test_api_response_types(client):
    """Test that API responses have correct types."""
    # Test status endpoint
    response = client.get("/api/v1/status")
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data["status"], str)
        assert isinstance(data["uptime_seconds"], int)
        assert isinstance(data["total_emails_processed"], int)

    # Test config endpoint
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["webhook_configured"], bool)
