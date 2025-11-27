"""
Pytest configuration and shared fixtures.

Provides test database, FastAPI client, and mocked dependencies.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.channels.factory import ChannelFactory
from src.templates.engine import TemplateEngine
from src.services.notification_service import NotificationService


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def mock_db_pool():
    """Mock database pool."""
    pool = AsyncMock()
    pool.acquire = AsyncMock()
    return pool


@pytest.fixture
async def channel_factory():
    """Create mock channel factory."""
    factory = ChannelFactory()
    factory.channels = {}
    return factory


@pytest.fixture
async def template_engine():
    """Create template engine."""
    engine = TemplateEngine()
    return engine


@pytest.fixture
async def notification_service(channel_factory, template_engine):
    """Create notification service."""
    return NotificationService(channel_factory, template_engine)


@pytest.fixture
def sample_analysis():
    """Sample analysis data for testing."""
    return {
        "id": "test-analysis-123",
        "report_id": "test-report-456",
        "title": "Trading Analysis",
        "summary": "Market analysis summary",
        "sentiment": "bullish",
        "confidence_score": 0.85,
        "trading_signals": [
            {
                "action": "BUY",
                "symbol": "AAPL",
                "entry_price": 150.0,
                "target_price": 160.0,
                "confidence_score": 0.9,
            }
        ],
        "market_insights": ["Market trend is bullish"],
        "symbols_mentioned": ["AAPL", "MSFT"],
        "price_targets": {"AAPL": 160.0},
        "ai_provider": "anthropic",
        "win_rate": 75.5,
        "profit_loss": 1500.0,
    }


@pytest.fixture
def sample_notification_request():
    """Sample notification request."""
    return {
        "analysis_id": "test-analysis-123",
        "report_id": "test-report-456",
        "channels": ["email", "telegram"],
        "recipients": {
            "email": "test@example.com",
            "telegram": "123456789",
        },
        "message_type": "summary",
    }
