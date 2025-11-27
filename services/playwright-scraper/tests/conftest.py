"""
Pytest configuration and fixtures.

Provides reusable fixtures for testing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.config import Config


@pytest.fixture
def config():
    """Provide test configuration."""
    return Config()


@pytest.fixture
def mock_page():
    """Provide mock Playwright page."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.query_selector = AsyncMock(return_value=MagicMock())
    page.locator = MagicMock()
    page.screenshot = AsyncMock(return_value=b"fake_image_data")
    return page


@pytest.fixture
def mock_browser_context():
    """Provide mock Playwright browser context."""
    context = AsyncMock()
    context.new_page = AsyncMock()
    context.close = AsyncMock()
    return context


@pytest.fixture
def mock_browser():
    """Provide mock Playwright browser."""
    browser = AsyncMock()
    browser.new_context = AsyncMock()
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def sample_html():
    """Provide sample HTML for testing."""
    return """
    <article>
        <h2>Sample Report Title</h2>
    </article>
    <div class="entry-content">
        <p>Report content here</p>
        <img src="https://www.tradingview.com/x/km6wgmVI/" width="1595" height="902" />
        <img src="/local/image.png" width="800" height="600" />
        <script>alert('xss');</script>
    </div>
    """


@pytest.fixture
def sample_cleaned_html():
    """Provide sample cleaned HTML (scripts removed)."""
    return """
    <article>
        <h2>Sample Report Title</h2>
    </article>
    <div class="entry-content">
        <p>Report content here</p>
        <img src="https://www.tradingview.com/x/km6wgmVI/" width="1595" height="902" />
        <img src="/local/image.png" width="800" height="600" />
    </div>
    """
