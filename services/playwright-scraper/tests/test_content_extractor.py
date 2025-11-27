"""Tests for main ContentExtractor service."""

import pytest
import asyncio
from src.content_extraction.extractor import ContentExtractor, extract_trading_report
from src.content_extraction.config import ExtractionConfig


class TestContentExtractor:
    """Test main content extraction service."""

    @pytest.mark.asyncio
    async def test_extract_from_valid_html(self):
        """Verify extraction works with valid HTML."""
        html = '''
        <html>
        <body>
            <div class="avatar-info-component-container">
                <div class="name">John Trader</div>
                <div class="text-info">26 de noviembre de 2025 a las 15:44</div>
            </div>
            <article class="pts-analysis">
                <div class="entry-content">
                    <h2>Trading Analysis</h2>
                    <p>This is a trading analysis report.</p>
                    <img src="https://example.com/chart.png" alt="Chart" />
                </div>
            </article>
        </body>
        </html>
        '''

        extractor = ContentExtractor()
        result = await extractor.extract_from_html(
            html=html,
            report_url="https://example.com/report",
            page_base_url="https://example.com/report",
            correlation_id="test-123",
        )

        assert result.success is True
        assert result.extracted_text is not None
        assert "Trading Analysis" in result.extracted_text or "analysis" in result.extracted_text.lower()

    @pytest.mark.asyncio
    async def test_extract_metadata_fields(self):
        """Verify author, date, and title are extracted."""
        html = '''
        <html>
        <body>
            <div class="avatar-info-component-container">
                <div class="name">Jane Smith</div>
                <div class="text-info">15 de enero de 2025 a las 10:30</div>
            </div>
            <article class="pts-analysis">
                <div class="entry-content">
                    <h2>My Title</h2>
                    <p>Content here</p>
                </div>
            </article>
        </body>
        </html>
        '''

        extractor = ContentExtractor()
        result = await extractor.extract_from_html(
            html=html,
            report_url="https://example.com/report",
            page_base_url="https://example.com/report",
            correlation_id="test-123",
        )

        assert result.success is True
        assert result.author == "Jane Smith"
        assert result.publication_date is not None
        assert result.title is not None

    @pytest.mark.asyncio
    async def test_extract_with_missing_author(self):
        """Verify extraction succeeds even without author."""
        html = '''
        <html>
        <body>
            <article class="pts-analysis">
                <div class="entry-content">
                    <h2>Title</h2>
                    <p>Content</p>
                </div>
            </article>
        </body>
        </html>
        '''

        extractor = ContentExtractor()
        result = await extractor.extract_from_html(
            html=html,
            report_url="https://example.com/report",
            page_base_url="https://example.com/report",
            correlation_id="test-123",
        )

        assert result.success is True
        assert result.author is None  # Missing author is acceptable
        assert result.extracted_text is not None

    @pytest.mark.asyncio
    async def test_extraction_with_no_images(self):
        """Verify extraction works with no images."""
        html = '''
        <article class="pts-analysis">
            <div class="entry-content">
                <h2>Title</h2>
                <p>Content without images</p>
            </div>
        </article>
        '''

        extractor = ContentExtractor()
        result = await extractor.extract_from_html(
            html=html,
            report_url="https://example.com/report",
            page_base_url="https://example.com/report",
            correlation_id="test-123",
        )

        assert result.success is True
        assert len(result.extracted_images) == 0

    @pytest.mark.asyncio
    async def test_extraction_timing_recorded(self):
        """Verify extraction duration is recorded."""
        html = '''
        <article class="pts-analysis">
            <div class="entry-content">
                <p>Quick content</p>
            </div>
        </article>
        '''

        extractor = ContentExtractor()
        result = await extractor.extract_from_html(
            html=html,
            report_url="https://example.com/report",
            page_base_url="https://example.com/report",
            correlation_id="test-123",
        )

        assert result.success is True
        assert result.duration_ms > 0
        assert result.duration_ms < 5000  # Should be fast

    @pytest.mark.asyncio
    async def test_extraction_with_invalid_html(self):
        """Verify extraction handles invalid input gracefully."""
        extractor = ContentExtractor()
        result = await extractor.extract_from_html(
            html="",  # Empty HTML
            report_url="https://example.com/report",
            page_base_url="https://example.com/report",
            correlation_id="test-123",
        )

        assert result.success is False
        assert result.error_message is not None


class TestExtractTradingReportFunction:
    """Test public extract_trading_report API."""

    @pytest.mark.asyncio
    async def test_public_api_works(self):
        """Verify public API function works correctly."""
        html = '''
        <article class="pts-analysis">
            <div class="entry-content">
                <p>Test content</p>
            </div>
        </article>
        '''

        result = await extract_trading_report(
            html=html,
            report_url="https://example.com/report",
            page_base_url="https://example.com/report",
            correlation_id="test-123",
        )

        assert result is not None
        assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_public_api_with_report_id(self):
        """Verify public API accepts report_id for logging."""
        html = '''
        <article class="pts-analysis">
            <div class="entry-content">
                <p>Content</p>
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

        assert result is not None
        assert result.success is True
