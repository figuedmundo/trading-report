"""
Tests for authentication flow.

Tests login success, retry logic, and credential validation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.browser import BrowserManager
from src.config import Config
from src.utils.exceptions import LoginError, CredentialError


@pytest.mark.asyncio
async def test_login_successful(config):
    """Verify successful login flow."""
    manager = BrowserManager(config)
    manager.page = AsyncMock()
    manager.page.goto = AsyncMock()
    manager.page.fill = AsyncMock()
    manager.page.click = AsyncMock()
    manager.page.wait_for_load_state = AsyncMock()

    # Mock successful login
    await manager.login(username="testuser", password="testpass")

    # Verify login steps
    manager.page.goto.assert_called_once()
    manager.page.fill.assert_any_call(config.username_selector, "testuser")
    manager.page.fill.assert_any_call(config.password_selector, "testpass")
    manager.page.click.assert_called_once()
    manager.page.wait_for_load_state.assert_called_once()


@pytest.mark.asyncio
async def test_login_credentials_required(config):
    """Verify login fails if credentials missing."""
    manager = BrowserManager(config)
    manager.page = AsyncMock()

    with pytest.raises(CredentialError):
        await manager.login(username=None, password=None)


@pytest.mark.asyncio
async def test_login_retry_on_failure(config):
    """Verify login retries with exponential backoff on failure."""
    manager = BrowserManager(config)
    manager.page = AsyncMock()
    manager.page.goto = AsyncMock()
    manager.page.fill = AsyncMock()
    manager.page.click = AsyncMock()

    # Mock failure then success
    manager.page.wait_for_load_state = AsyncMock(
        side_effect=[
            Exception("Network error"),
            Exception("Timeout"),
            None,  # Success on 3rd attempt
        ]
    )

    with patch("asyncio.sleep") as mock_sleep:
        result = await manager.login(username="testuser", password="testpass")

    # Should succeed after retries
    assert result is True
    # Verify backoff delays: 1s, 2s, (4s not needed for success)
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


@pytest.mark.asyncio
async def test_login_failure_after_retries(config):
    """Verify login fails after max retries exhausted."""
    manager = BrowserManager(config)
    manager.page = AsyncMock()
    manager.page.goto = AsyncMock()
    manager.page.fill = AsyncMock()
    manager.page.click = AsyncMock()

    # Mock continuous failures
    manager.page.wait_for_load_state = AsyncMock(
        side_effect=Exception("Persistent network error")
    )

    with patch("asyncio.sleep"):
        with pytest.raises(LoginError):
            await manager.login(username="testuser", password="testpass")


@pytest.mark.asyncio
async def test_needs_login_detection(config):
    """Verify login requirement detection."""
    manager = BrowserManager(config)
    manager.page = AsyncMock()

    # Test: login required
    manager.page.query_selector = AsyncMock(return_value=MagicMock())
    assert await manager.needs_login() is True

    # Test: login not required
    manager.page.query_selector = AsyncMock(return_value=None)
    assert await manager.needs_login() is False
