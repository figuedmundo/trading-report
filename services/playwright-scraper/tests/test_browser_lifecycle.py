"""
Tests for browser lifecycle management.

Tests browser launch, configuration, and cleanup.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.browser import BrowserManager
from src.config import Config


@pytest.mark.asyncio
async def test_browser_launches_successfully():
    """Verify browser launches with correct viewport and configuration."""
    with patch("src.browser.async_playwright") as mock_playwright:
        # Mock playwright
        mock_pw_instance = AsyncMock()
        mock_playwright.return_value.__aenter__.return_value = mock_pw_instance

        # Mock browser and page
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        # Test
        config = Config()
        manager = BrowserManager(config)

        async with manager:
            assert manager.browser == mock_browser
            assert manager.page == mock_page

        # Verify browser was launched with correct args
        mock_pw_instance.chromium.launch.assert_called_once()
        call_kwargs = mock_pw_instance.chromium.launch.call_args[1]
        assert call_kwargs["headless"] == config.playwright_headless
        assert "--no-sandbox" in call_kwargs["args"]
        assert "--disable-dev-shm-usage" in call_kwargs["args"]


@pytest.mark.asyncio
async def test_browser_cleanup_on_exit():
    """Verify browser cleanup is called on context exit."""
    with patch("src.browser.async_playwright") as mock_playwright:
        # Mock playwright
        mock_pw_instance = AsyncMock()
        mock_playwright.return_value.__aenter__.return_value = mock_pw_instance

        # Mock browser and page
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        # Test
        manager = BrowserManager()

        async with manager:
            pass

        # Verify cleanup was called
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_pw_instance.stop.assert_called_once()


@pytest.mark.asyncio
async def test_browser_cleanup_on_exception():
    """Verify browser cleanup happens even on exception."""
    with patch("src.browser.async_playwright") as mock_playwright:
        # Mock playwright
        mock_pw_instance = AsyncMock()
        mock_playwright.return_value.__aenter__.return_value = mock_pw_instance

        # Mock browser and page
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        # Test exception handling
        manager = BrowserManager()

        try:
            async with manager:
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify cleanup was still called
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
