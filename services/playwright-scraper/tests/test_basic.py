"""Basic tests for playwright-scraper service."""

import pytest
from fastapi.testclient import TestClient
from src.main import app


def test_health_endpoint():
    """Test health check endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "playwright-scraper"
    assert data["version"] == "0.1.0"
