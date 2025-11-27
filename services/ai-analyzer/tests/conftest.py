"""
Pytest configuration and fixtures.

Provides common fixtures for tests across the service.
"""

import pytest
import sys
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("SERVICE_PORT", "8002")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("ANALYSIS_TIMEOUT", "30")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
