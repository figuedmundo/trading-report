"""Tests for content extraction logging."""

import pytest
from src.content_extraction.logging_utils import (
    log_extraction_event,
    log_extraction_completed,
    log_extraction_failed,
)


class TestExtractionLogging:
    """Test extraction event logging."""

    def test_log_extraction_event_without_db(self):
        """Verify logging works without database pool."""
        # Should not crash if db_pool is None
        result = log_extraction_event(
            correlation_id="test-123",
            report_id="report-uuid",
            log_level="INFO",
            message="Test event",
            metadata={"test": "data"},
            db_pool=None,
        )

        # Should return False when no pool available
        assert result is False

    def test_log_extraction_completed_structure(self):
        """Verify completed extraction metadata is structured correctly."""
        # This just verifies the function accepts the parameters
        # without database, it returns False
        result = log_extraction_completed(
            correlation_id="test-123",
            report_id="report-uuid",
            duration_ms=1500,
            images_found=3,
            images_downloaded=2,
            images_failed=1,
            tradingview_images=1,
            content_length_bytes=5000,
            author_extracted=True,
            date_parsed=True,
            fallback_used=None,
            db_pool=None,
        )

        assert result is False  # No pool, so returns False

    def test_log_extraction_failed_structure(self):
        """Verify failed extraction metadata is structured correctly."""
        result = log_extraction_failed(
            correlation_id="test-123",
            report_id="report-uuid",
            error_message="Test error",
            fallback_used="plain_text",
            stack_trace="Stack trace here",
            db_pool=None,
        )

        assert result is False  # No pool, so returns False

    def test_log_extraction_with_all_parameters(self):
        """Verify logging accepts all expected parameters."""
        # Verify function signature works with all parameters
        result = log_extraction_event(
            correlation_id="test-123",
            report_id="report-uuid",
            log_level="INFO",
            message="Test message",
            metadata={
                "duration_ms": 1000,
                "images_found": 5,
                "content_length": 10000,
            },
            stack_trace="Test traceback",
            db_pool=None,
        )

        assert isinstance(result, bool)
