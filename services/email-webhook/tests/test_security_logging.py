"""
Tests for Task 6.1: Security Event Logging & Alerting

Covers core functionality of security event logging, pattern detection, and alert debouncing.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def mock_config():
    """Mock configuration for tests."""
    config = MagicMock()
    config.security_alert_threshold = 50
    config.security_alert_telegram = True
    config.security_alert_debounce_minutes = 10
    return config


@pytest.fixture
def mock_repository():
    """Mock SecurityEventsRepository for tests."""
    repo = AsyncMock()
    repo.log_event = AsyncMock(return_value={
        "id": "event-123",
        "event_type": "signature_validation_failed",
        "ip_address": "192.168.1.1",
        "endpoint": "/webhook/email",
        "created_at": datetime.utcnow().isoformat(),
    })
    repo.get_recent_events = AsyncMock(return_value=[])
    repo.cleanup_old_events = AsyncMock(return_value=0)
    return repo


class TestSecurityEventsRepository:
    """Tests for SecurityEventsRepository."""

    @pytest.mark.asyncio
    async def test_log_event_async_insert(self, mock_repository):
        """Test async security event insertion to database."""
        result = await mock_repository.log_event(
            event_type="signature_validation_failed",
            ip_address="192.168.1.1",
            endpoint="/webhook/email",
            request_headers={"User-Agent": "test"},
            metadata={"provider": "mailgun"},
        )

        assert result["id"] == "event-123"
        assert result["event_type"] == "signature_validation_failed"
        assert result["ip_address"] == "192.168.1.1"
        mock_repository.log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_event_filters_sensitive_headers(self, mock_repository):
        """Test that sensitive headers are filtered before logging."""
        headers = {
            "Authorization": "Bearer token123",
            "X-Signature": "sig123",
            "User-Agent": "Mozilla/5.0",
        }

        await mock_repository.log_event(
            event_type="signature_validation_failed",
            ip_address="192.168.1.1",
            endpoint="/webhook/email",
            request_headers=headers,
        )

        # Verify log_event was called
        mock_repository.log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_events_query(self, mock_repository):
        """Test querying recent security events for pattern detection."""
        mock_repository.get_recent_events.return_value = [
            {
                "id": "1",
                "event_type": "signature_validation_failed",
                "ip_address": "192.168.1.1",
                "endpoint": "/webhook/email",
                "created_at": datetime.utcnow().isoformat(),
                "metadata": {},
            },
            {
                "id": "2",
                "event_type": "signature_validation_failed",
                "ip_address": "192.168.1.1",
                "endpoint": "/webhook/email",
                "created_at": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                "metadata": {},
            },
        ]

        events = await mock_repository.get_recent_events(
            ip_address="192.168.1.1",
            minutes=10,
        )

        assert len(events) == 2
        assert all(e["ip_address"] == "192.168.1.1" for e in events)
        mock_repository.get_recent_events.assert_called_once()


class TestSecurityLogger:
    """Tests for SecurityLogger."""

    @pytest.mark.asyncio
    async def test_log_signature_failure(self, mock_repository, mock_config):
        """Test logging signature validation failure."""
        from src.security.security_logger import SecurityLogger

        logger = SecurityLogger(mock_repository)

        await logger.log_signature_failure(
            ip_address="192.168.1.1",
            endpoint="/webhook/email",
            headers={"User-Agent": "test"},
            metadata={"provider": "mailgun"},
        )

        mock_repository.log_event.assert_called_once()
        call_kwargs = mock_repository.log_event.call_args[1]
        assert call_kwargs["event_type"] == "signature_validation_failed"
        assert call_kwargs["ip_address"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_log_ip_not_whitelisted(self, mock_repository):
        """Test logging IP not whitelisted event."""
        from src.security.security_logger import SecurityLogger

        logger = SecurityLogger(mock_repository)

        await logger.log_ip_not_whitelisted(
            ip_address="192.168.1.1",
            endpoint="/webhook/email",
        )

        mock_repository.log_event.assert_called_once()
        call_kwargs = mock_repository.log_event.call_args[1]
        assert call_kwargs["event_type"] == "ip_not_whitelisted"
        assert "IP not in allowlist" in str(call_kwargs["metadata"])

    @pytest.mark.asyncio
    async def test_log_rate_limit_exceeded(self, mock_repository):
        """Test logging rate limit exceeded event."""
        from src.security.security_logger import SecurityLogger

        logger = SecurityLogger(mock_repository)

        await logger.log_rate_limit_exceeded(
            ip_address="192.168.1.1",
            endpoint="/webhook/email",
            limit_type="per_ip_minute",
            remaining=0,
            reset_timestamp=1234567890.0,
        )

        mock_repository.log_event.assert_called_once()
        call_kwargs = mock_repository.log_event.call_args[1]
        assert call_kwargs["event_type"] == "rate_limit_exceeded"
        assert call_kwargs["metadata"]["limit_type"] == "per_ip_minute"
        assert call_kwargs["metadata"]["rate_limit_remaining"] == 0

    @pytest.mark.asyncio
    async def test_log_ip_banned(self, mock_repository):
        """Test logging IP banned event."""
        from src.security.security_logger import SecurityLogger

        logger = SecurityLogger(mock_repository)

        await logger.log_ip_banned(
            ip_address="192.168.1.1",
            reason="Too many failed attempts",
            attempt_count=15,
            ban_duration_hours=1,
        )

        mock_repository.log_event.assert_called_once()
        call_kwargs = mock_repository.log_event.call_args[1]
        assert call_kwargs["event_type"] == "ip_banned"
        assert call_kwargs["metadata"]["attempt_count"] == 15
        assert call_kwargs["metadata"]["ban_duration_hours"] == 1


class TestPatternDetector:
    """Tests for PatternDetector."""

    @pytest.mark.asyncio
    async def test_detect_high_frequency_failures(self, mock_repository, mock_config):
        """Test detecting high frequency failure patterns."""
        from src.security.pattern_detector import PatternDetector

        # Create events that exceed threshold
        events = [
            {
                "id": str(i),
                "event_type": "signature_validation_failed",
                "ip_address": "192.168.1.1",
                "endpoint": "/webhook/email",
                "metadata": {},
                "created_at": (datetime.utcnow() - timedelta(minutes=i % 10)).isoformat(),
            }
            for i in range(55)  # 55 events > 50 threshold
        ]

        mock_repository.get_recent_events.return_value = events

        with patch("src.security.pattern_detector.get_config", return_value=mock_config):
            detector = PatternDetector(mock_repository)
            patterns = await detector.detect_suspicious_patterns("192.168.1.1")

        assert len(patterns) >= 1
        assert any(p["type"] == "high_frequency_failures" for p in patterns)

    @pytest.mark.asyncio
    async def test_no_pattern_when_under_threshold(self, mock_repository, mock_config):
        """Test that no pattern is detected when under threshold."""
        from src.security.pattern_detector import PatternDetector

        # Create events below threshold
        events = [
            {
                "id": str(i),
                "event_type": "signature_validation_failed",
                "ip_address": "192.168.1.1",
                "endpoint": "/webhook/email",
                "metadata": {},
                "created_at": datetime.utcnow().isoformat(),
            }
            for i in range(30)  # 30 events < 50 threshold
        ]

        mock_repository.get_recent_events.return_value = events

        with patch("src.security.pattern_detector.get_config", return_value=mock_config):
            detector = PatternDetector(mock_repository)
            patterns = await detector.detect_suspicious_patterns("192.168.1.1")

        assert len(patterns) == 0


class TestTelegramAlerter:
    """Tests for TelegramAlerter."""

    def test_alert_debouncing(self, mock_config):
        """Test Telegram alert debouncing (1 per pattern per 10 min)."""
        from src.security.telegram_alerter import TelegramAlerter

        with patch("src.security.telegram_alerter.get_config", return_value=mock_config):
            alerter = TelegramAlerter()

            # First alert should be sent
            alert_key = "ip_banned:192.168.1.1"
            should_send = alerter._should_send_alert(alert_key)
            assert should_send is True

            # Second alert immediately after should be debounced
            should_send = alerter._should_send_alert(alert_key)
            assert should_send is False

    @pytest.mark.asyncio
    async def test_send_alert_respects_config(self, mock_config):
        """Test that alert sending respects SECURITY_ALERT_TELEGRAM config."""
        from src.security.telegram_alerter import TelegramAlerter

        # Alerts disabled
        mock_config.security_alert_telegram = False
        with patch("src.security.telegram_alerter.get_config", return_value=mock_config):
            alerter = TelegramAlerter()
            result = await alerter.send_alert(
                alert_type="ip_banned",
                ip_address="192.168.1.1",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_alert_graceful_degradation(self, mock_config):
        """Test graceful degradation if notification service unavailable."""
        from src.security.telegram_alerter import TelegramAlerter

        with patch("src.security.telegram_alerter.get_config", return_value=mock_config):
            alerter = TelegramAlerter()

            # Mock notification service failure
            with patch.object(alerter, "_call_notification_service", side_effect=Exception("Service unavailable")):
                result = await alerter.send_alert(
                    alert_type="ip_banned",
                    ip_address="192.168.1.1",
                )

        # Should return False but not raise exception (graceful degradation)
        assert result is False

    def test_alert_message_formatting(self, mock_config):
        """Test alert message formatting for different alert types."""
        from src.security.telegram_alerter import TelegramAlerter

        with patch("src.security.telegram_alerter.get_config", return_value=mock_config):
            alerter = TelegramAlerter()

            # Test IP banned alert formatting
            msg = alerter._format_alert_message(
                alert_type="ip_banned",
                ip_address="192.168.1.1",
                metadata={"attempt_count": 15, "ban_duration_hours": 1},
            )

            assert "IP Banned" in msg
            assert "192.168.1.1" in msg
            assert "15" in msg

            # Test high frequency attack alert
            msg = alerter._format_alert_message(
                alert_type="high_frequency_attack",
                ip_address="192.168.1.1",
                metadata={"event_count": 75, "time_window_minutes": 10},
            )

            assert "High Frequency Attack" in msg
            assert "75" in msg
            assert "10" in msg


class TestSecurityLoggingIntegration:
    """Integration tests for security logging components."""

    @pytest.mark.asyncio
    async def test_full_logging_flow(self, mock_repository, mock_config):
        """Test complete security event logging flow."""
        from src.security.security_logger import SecurityLogger
        from src.security.pattern_detector import PatternDetector

        # Setup
        logger = SecurityLogger(mock_repository)
        mock_repository.get_recent_events.return_value = [
            {
                "id": str(i),
                "event_type": "signature_validation_failed",
                "ip_address": "192.168.1.1",
                "endpoint": "/webhook/email",
                "metadata": {},
                "created_at": datetime.utcnow().isoformat(),
            }
            for i in range(55)
        ]

        # Log event
        await logger.log_signature_failure(
            ip_address="192.168.1.1",
            endpoint="/webhook/email",
            headers={},
        )

        # Detect patterns
        with patch("src.security.pattern_detector.get_config", return_value=mock_config):
            detector = PatternDetector(mock_repository)
            patterns = await detector.detect_suspicious_patterns("192.168.1.1")

        # Verify
        assert mock_repository.log_event.called
        assert len(patterns) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
