"""Tests for image handling and downloading."""

import pytest
from src.content_extraction.image_handler import (
    is_tradingview_image,
    validate_url,
    resolve_relative_url,
    encode_image_to_base64,
    build_image_metadata,
)
from src.content_extraction.config import ExtractionConfig


class TestTradingViewDetection:
    """Test TradingView URL detection."""

    def test_detect_tradingview_com_urls(self):
        """Verify tradingview.com URLs are detected."""
        urls = [
            "https://tradingview.com/chart/EURUSD",
            "https://www.tradingview.com/embed",
            "http://tradingview.com/analysis",
        ]

        for url in urls:
            assert is_tradingview_image(url) is True

    def test_detect_tradingview_net_urls(self):
        """Verify tradingview.net URLs are detected."""
        url = "https://www.tradingview.net/chart"

        assert is_tradingview_image(url) is True

    def test_detect_tv_com_urls(self):
        """Verify tv.com URLs are detected."""
        url = "https://tv.com/analysis"

        assert is_tradingview_image(url) is True

    def test_reject_regular_image_urls(self):
        """Verify non-TradingView URLs are not detected."""
        urls = [
            "https://example.com/image.png",
            "https://broker.com/chart.png",
            "https://cdn.example.com/screenshot.jpg",
        ]

        for url in urls:
            assert is_tradingview_image(url) is False

    def test_case_insensitive_matching(self):
        """Verify URL matching is case-insensitive."""
        url = "https://TRADINGVIEW.COM/chart"

        assert is_tradingview_image(url) is True


class TestUrlValidation:
    """Test URL validation."""

    def test_validate_https_urls(self):
        """Verify HTTPS URLs are valid."""
        assert validate_url("https://example.com/image.png") is True

    def test_validate_http_urls(self):
        """Verify HTTP URLs are valid."""
        assert validate_url("http://example.com/image.png") is True

    def test_reject_relative_urls(self):
        """Verify relative URLs are rejected."""
        assert validate_url("image.png") is False
        assert validate_url("/images/test.png") is False
        assert validate_url("../images/test.png") is False

    def test_reject_invalid_urls(self):
        """Verify invalid URLs are rejected."""
        assert validate_url("") is False
        assert validate_url(None) is False
        assert validate_url("ftp://example.com/file") is False


class TestRelativeUrlResolution:
    """Test relative URL to absolute conversion."""

    def test_resolve_root_relative_url(self):
        """Verify /path URLs are resolved correctly."""
        result = resolve_relative_url(
            "/static/logo.png",
            "https://example.com/blog/article/"
        )

        assert result == "https://example.com/static/logo.png"

    def test_resolve_current_directory_url(self):
        """Verify ./path URLs are resolved correctly."""
        result = resolve_relative_url(
            "./image.png",
            "https://example.com/blog/article/"
        )

        assert result == "https://example.com/blog/article/image.png"

    def test_resolve_parent_directory_url(self):
        """Verify ../path URLs are resolved correctly."""
        result = resolve_relative_url(
            "../images/chart.png",
            "https://example.com/blog/article/"
        )

        assert result == "https://example.com/blog/images/chart.png"

    def test_preserve_absolute_urls(self):
        """Verify absolute URLs are not modified."""
        url = "https://cdn.example.com/images/chart.png"

        result = resolve_relative_url(url, "https://other.com/page/")

        assert result == url


class TestBase64Encoding:
    """Test image base64 encoding."""

    def test_encode_valid_image_bytes(self):
        """Verify valid image bytes are encoded."""
        # Create minimal PNG bytes (100+ bytes)
        image_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 200

        result = encode_image_to_base64(image_bytes)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_reject_empty_image_bytes(self):
        """Verify empty image bytes return None."""
        result = encode_image_to_base64(b'')

        assert result is None

    def test_reject_small_image_bytes(self):
        """Verify small image bytes (< 100 bytes) return None."""
        result = encode_image_to_base64(b'\x89PNG\r\n\x1a\n' + b'\x00' * 50)

        assert result is None

    def test_reject_none_image_bytes(self):
        """Verify None input returns None."""
        result = encode_image_to_base64(None)

        assert result is None


class TestImageMetadataBuilding:
    """Test image metadata JSONB structure."""

    def test_build_basic_metadata(self):
        """Verify basic image metadata is built correctly."""
        metadata = build_image_metadata(
            url="https://example.com/image.png",
            content_type="image/png",
            position_index=0,
        )

        assert metadata["url"] == "https://example.com/image.png"
        assert metadata["content_type"] == "image/png"
        assert metadata["position_index"] == 0
        assert metadata["is_tradingview"] is False
        assert metadata["download_status"] == "success"

    def test_include_base64_data_when_provided(self):
        """Verify base64 data is included in metadata."""
        base64_data = "iVBORw0KGgoAAAANS..."
        metadata = build_image_metadata(
            url="local://image-0",
            content_type="image/png",
            position_index=0,
            base64_data=base64_data,
        )

        assert metadata["base64_data"] == base64_data

    def test_omit_base64_data_when_not_provided(self):
        """Verify base64 data is omitted if not provided."""
        metadata = build_image_metadata(
            url="https://example.com/image.png",
            content_type="image/png",
            position_index=0,
        )

        assert "base64_data" not in metadata

    def test_include_dimensions_when_provided(self):
        """Verify image dimensions are included."""
        metadata = build_image_metadata(
            url="https://example.com/image.png",
            content_type="image/png",
            position_index=0,
            width=800,
            height=600,
        )

        assert metadata["width"] == 800
        assert metadata["height"] == 600

    def test_mark_tradingview_images(self):
        """Verify TradingView flag is set correctly."""
        metadata = build_image_metadata(
            url="https://tradingview.com/chart",
            content_type="text/html",
            position_index=0,
            is_tradingview=True,
            download_status="tradingview_link",
        )

        assert metadata["is_tradingview"] is True
        assert metadata["download_status"] == "tradingview_link"
