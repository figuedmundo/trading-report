"""
Tests for API endpoint functionality.

Tests POST /api/v1/analyze and GET /health endpoints.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


def test_health_check_endpoint(client):
    """Test GET /health endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "ai-analyzer"
    assert response.json()["version"] == "0.1.0"


def test_analyze_endpoint_success(client):
    """Test successful POST /api/v1/analyze request."""
    sample_request = {
        "report_id": "test-report-123",
        "raw_extracted_text": "BTC strong buy signal with target 45000. ETH sell signal at 2500.",
    }

    with patch('src.api.routes._analysis_service') as mock_service:
        mock_service = MagicMock()
        mock_service.analyze = AsyncMock(return_value=MagicMock(
            report_id="test-report-123",
            api_provider="fallback_keyword",
            summary="Test summary",
            trading_signals=[],
            market_insights=[],
            symbols_mentioned=["BTC", "ETH"],
            price_targets={"BTC": 45000.0, "ETH": 2500.0},
            raw_extracted_text=sample_request["raw_extracted_text"],
        ))

        with patch('src.api.routes._analysis_service', mock_service):
            response = client.post("/api/v1/analyze", json=sample_request)

        assert response.status_code == 200
        data = response.json()
        assert data["report_id"] == "test-report-123"
        assert data["api_provider"] in ["anthropic", "groq", "fallback_keyword"]


def test_analyze_endpoint_missing_report_id(client):
    """Test POST /api/v1/analyze with missing report_id."""
    sample_request = {
        "raw_extracted_text": "BTC strong buy signal with target 45000.",
    }

    response = client.post("/api/v1/analyze", json=sample_request)

    # Missing required field should return 422 (validation error)
    assert response.status_code == 422


def test_analyze_endpoint_empty_text(client):
    """Test POST /api/v1/analyze with empty raw_extracted_text."""
    sample_request = {
        "report_id": "test-report-123",
        "raw_extracted_text": "",
    }

    response = client.post("/api/v1/analyze", json=sample_request)

    # Empty text should be caught by Pydantic validation
    assert response.status_code == 422


def test_analyze_endpoint_invalid_json(client):
    """Test POST /api/v1/analyze with invalid JSON."""
    response = client.post(
        "/api/v1/analyze",
        data="not valid json",
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_endpoint_response_structure():
    """Test that analyze endpoint returns correct response structure."""
    from src.models import AnalysisSuccessResponse

    # Create a sample response
    response = AnalysisSuccessResponse(
        report_id="test-123",
        api_provider="fallback_keyword",
        summary="Test summary",
        trading_signals=[],
        market_insights=[],
        symbols_mentioned=["BTC"],
        price_targets={},
        raw_extracted_text="Test content",
    )

    # Verify fields
    assert response.report_id == "test-123"
    assert response.api_provider == "fallback_keyword"
    assert isinstance(response.trading_signals, list)
    assert isinstance(response.market_insights, list)
    assert isinstance(response.symbols_mentioned, list)
    assert isinstance(response.price_targets, dict)


def test_health_check_response_format(client):
    """Test health check response format."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields
    assert "status" in data
    assert "service" in data
    assert "version" in data

    # Verify types
    assert isinstance(data["status"], str)
    assert isinstance(data["service"], str)
    assert isinstance(data["version"], str)
