"""
Tests for Task Group 6: URL Extraction & Portal Validation
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from extractors import (
    extract_urls_from_text,
    extract_urls_from_html_href,
    extract_all_urls,
    validate_url_format,
    filter_urls_by_trusted_domains,
)


class TestURLExtraction:
    """Test URL extraction from text and HTML."""

    def test_extract_urls_from_plain_text(self):
        """Test URL extraction from plain text."""
        text = "Visit https://protradingskills.com/analysis/123 for details."
        urls = extract_urls_from_text(text)
        assert len(urls) > 0
        assert "https://protradingskills.com/analysis/123" in urls

    def test_extract_urls_from_html_href(self):
        """Test URL extraction from HTML href attributes."""
        html = '<a href="https://example.com/report">Report</a>'
        urls = extract_urls_from_html_href(html)
        assert "https://example.com/report" in urls

    def test_extract_all_urls_combines_sources(self):
        """Test combining URLs from text and HTML."""
        text = "Check https://example.com/text"
        html = '<a href="https://example.com/html">Link</a>'
        urls = extract_all_urls(text, html)
        assert "https://example.com/text" in urls
        assert "https://example.com/html" in urls

    def test_extract_urls_removes_duplicates(self):
        """Test that duplicate URLs are removed."""
        text = "https://example.com https://example.com"
        urls = extract_all_urls(text, "")
        assert urls.count("https://example.com") == 1


class TestURLValidation:
    """Test URL format validation."""

    def test_valid_https_url(self):
        """Test that valid HTTPS URL passes validation."""
        assert validate_url_format("https://example.com/path") is True

    def test_valid_http_url(self):
        """Test that valid HTTP URL passes validation."""
        assert validate_url_format("http://example.com/path") is True

    def test_invalid_url_no_scheme(self):
        """Test that URL without scheme fails validation."""
        assert validate_url_format("example.com/path") is False

    def test_invalid_url_bad_scheme(self):
        """Test that URL with non-http scheme fails validation."""
        assert validate_url_format("ftp://example.com/path") is False


class TestTrustedDomainFiltering:
    """Test filtering URLs by trusted domains."""

    def test_filter_urls_by_trusted_domain(self):
        """Test filtering URLs by trusted domain."""
        urls = [
            "https://protradingskills.com/analysis/123",
            "https://example.com/report",
            "https://protradingskills.com/analysis/456",
        ]

        with patch("extractors.get_config") as mock_config:
            config = MagicMock()
            config.trusted_domains = ["protradingskills.com"]
            mock_config.return_value = config

            first_url, additional, total = filter_urls_by_trusted_domains(urls)

            assert first_url is not None
            assert "protradingskills.com" in first_url
            assert total == 3

    def test_filter_urls_no_matching_domains(self):
        """Test filtering when no URLs match trusted domains."""
        urls = ["https://untrusted.com/report"]

        with patch("extractors.get_config") as mock_config:
            config = MagicMock()
            config.trusted_domains = ["protradingskills.com"]
            mock_config.return_value = config

            first_url, additional, total = filter_urls_by_trusted_domains(urls)

            assert first_url is None
            assert len(additional) == 0

    def test_filter_urls_case_insensitive_domain(self):
        """Test that domain filtering is case-insensitive."""
        urls = ["https://PROTRADINGSKILLS.COM/analysis/123"]

        with patch("extractors.get_config") as mock_config:
            config = MagicMock()
            config.trusted_domains = ["protradingskills.com"]
            mock_config.return_value = config

            first_url, additional, total = filter_urls_by_trusted_domains(urls)

            assert first_url is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
