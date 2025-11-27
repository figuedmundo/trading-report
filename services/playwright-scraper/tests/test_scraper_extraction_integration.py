"""Tests for scraper service integration with content extraction."""

import pytest
from src.content_extraction.extractor import extract_trading_report


class TestScraperExtractionIntegration:
    """Test integration of extraction with scraper service."""

    @pytest.mark.asyncio
    async def test_extraction_called_after_page_load(self):
        """Verify extraction can process HTML from page load."""
        html = '''
        <html>
        <body>
            <div class="avatar-info-component-container">
                <div class="name">Test Author</div>
                <div class="text-info">15 de noviembre de 2025 a las 10:30</div>
            </div>
            <article class="pts-analysis">
                <div class="entry-content">
                    <h2>Report Title</h2>
                    <p>Report content here</p>
                </div>
            </article>
        </body>
        </html>
        '''

        result = await extract_trading_report(
            html=html,
            report_url="https://example.com/report",
            page_base_url="https://example.com/report",
            correlation_id="test-123",
            report_id="report-uuid",
        )

        assert result.success is True
        assert result.extracted_text is not None

    @pytest.mark.asyncio
    async def test_database_update_would_include_extracted_content(self):
        """Verify extraction result has all fields for database update."""
        html = '''
        <article class="pts-analysis">
            <div class="entry-content">
                <h2>Title</h2>
                <p>Content</p>
                <img src="https://example.com/chart.png" />
            </div>
        </article>
        '''

        result = await extract_trading_report(
            html=html,
            report_url="https://example.com/report",
            page_base_url="https://example.com/report",
            correlation_id="test-123",
            report_id="report-uuid",
        )

        assert result.success is True
        # All fields needed for database update
        assert result.extracted_text is not None
        assert isinstance(result.extracted_images, list)
        assert hasattr(result, 'author')
        assert hasattr(result, 'publication_date')
        assert hasattr(result, 'title')

    @pytest.mark.asyncio
    async def test_extraction_failure_handled_gracefully(self):
        """Verify extraction failure doesn't crash scraper."""
        # Empty HTML should fail gracefully
        result = await extract_trading_report(
            html="",
            report_url="https://example.com/report",
            page_base_url="https://example.com/report",
            correlation_id="test-123",
            report_id="report-uuid",
        )

        # Should return error result, not crash
        assert result is not None
        assert result.success is False
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_status_transition_metadata_available(self):
        """Verify extraction provides metadata for status transitions."""
        html = '''
        <article class="pts-analysis">
            <div class="entry-content">
                <p>Quick report</p>
            </div>
        </article>
        '''

        result = await extract_trading_report(
            html=html,
            report_url="https://example.com/report",
            page_base_url="https://example.com/report",
            correlation_id="test-123",
            report_id="report-uuid",
        )

        assert result.success is True
        # Metadata for status update
        assert result.duration_ms >= 0
        assert result.images_downloaded >= 0
        assert result.images_failed >= 0
