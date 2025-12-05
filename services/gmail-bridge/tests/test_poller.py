"""Tests for Gmail Poller service."""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.gmail_poller import GmailPoller
from src.models import PollStats


@pytest.fixture
def poller():
    """Create a GmailPoller instance for testing."""
    with patch.dict('os.environ', {
        'SMTP_USER': 'test@gmail.com',
        'EMAIL_PASSWORD': 'test-password',
        'WEBHOOK_URL': 'http://localhost:5678/webhook',
    }):
        return GmailPoller()


def test_poller_initialization(poller):
    """Test poller initializes with correct configuration."""
    assert poller.config.SMTP_USER == 'test@gmail.com'
    assert poller.processed_uids == set()
    assert poller.is_running is False
    assert poller.total_emails_processed == 0


def test_extract_url_from_body(poller):
    """Test URL extraction from email body."""
    # Test with ProTradingSkills URL
    body = "Check this report: https://protradingskills.com/report/123"
    url = poller.extract_url_from_body(body)
    assert url == "https://protradingskills.com/report/123"

    # Test with multiple URLs (should prioritize ProTradingSkills)
    body = "See https://example.com and https://protradingskills.com/report/456"
    url = poller.extract_url_from_body(body)
    assert url == "https://protradingskills.com/report/456"

    # Test with no URL
    body = "No URL in this body"
    url = poller.extract_url_from_body(body)
    assert url is None

    # Test with generic URL
    body = "Check https://example.com/report/789"
    url = poller.extract_url_from_body(body)
    assert url == "https://example.com/report/789"


def test_parse_email(poller):
    """Test email parsing from raw bytes."""
    # Create a simple email
    raw_email = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Wed, 4 Dec 2025 12:00:00 +0000

This is a test email body.
https://protradingskills.com/report/123
"""
    parsed = poller.parse_email(raw_email)

    assert parsed is not None
    assert parsed['from'] == 'sender@example.com'
    assert parsed['subject'] == 'Test Email'
    assert 'test email body' in parsed['body'].lower()


@pytest.mark.asyncio
async def test_forward_to_webhook_success(poller):
    """Test successful webhook forwarding."""
    email_data = {
        "from": "test@example.com",
        "subject": "Test Report",
        "body": "Report at https://example.com/report/123",
        "to": "recipient@example.com",
        "date": "2025-12-04",
    }

    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response

        result = await poller.forward_to_webhook(email_data)
        assert result is True


@pytest.mark.asyncio
async def test_forward_to_webhook_failure(poller):
    """Test webhook forwarding with HTTP error."""
    email_data = {
        "from": "test@example.com",
        "subject": "Test Report",
        "body": "Report at https://example.com/report/123",
        "to": "recipient@example.com",
        "date": "2025-12-04",
    }

    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.text = MagicMock(return_value="Server error")
        mock_post.return_value.__aenter__.return_value = mock_response

        result = await poller.forward_to_webhook(email_data)
        assert result is False
        assert poller.total_errors > 0


@pytest.mark.asyncio
async def test_forward_to_webhook_no_url(poller):
    """Test webhook forwarding when no URL is found."""
    email_data = {
        "from": "test@example.com",
        "subject": "Test Report",
        "body": "No URL in this body",
        "to": "recipient@example.com",
        "date": "2025-12-04",
    }

    result = await poller.forward_to_webhook(email_data)
    assert result is False


def test_disconnect_imap(poller):
    """Test IMAP disconnection."""
    mock_client = MagicMock()
    poller.imap_client = mock_client

    poller.disconnect_imap()

    mock_client.logout.assert_called_once()
    assert poller.imap_client is None


def test_poller_state_management(poller):
    """Test poller state tracking."""
    # Initial state
    assert poller.is_running is False
    assert poller.last_poll_time is None
    assert poller.next_poll_time is None

    # After setting running
    poller.is_running = True
    now = datetime.utcnow()
    poller.last_poll_time = now

    assert poller.is_running is True
    assert poller.last_poll_time == now
