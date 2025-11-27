"""Configuration for content extraction module."""

from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class ExtractionConfig:
    """Configuration for HTML content extraction and image handling."""

    # CSS Selectors for ProTradingSkills
    author_selector: str = ".avatar-info-component-container .name"
    date_selector: str = ".avatar-info-component-container .text-info"
    article_selector: str = "article.pts-analysis .entry-content"
    title_selector: str = ".entry-content h2:first-of-type"
    image_selector: str = ".entry-content img"

    # Filter-out selectors (remove these elements)
    filter_selectors: List[str] = field(default_factory=lambda: [
        ".return-button-container",
        ".button-like",
        "script",
        "style",
        "meta",
        "link",
    ])

    # Allowed semantic HTML tags
    allowed_html_tags: Set[str] = field(default_factory=lambda: {
        "h1", "h2", "p", "img", "strong", "em", "ul", "li", "a"
    })

    # Image handling configuration
    max_image_size_mb: int = 5
    image_download_timeout_s: int = 10
    image_download_retries: int = 2
    max_parallel_images: int = 3

    # Supported image MIME types
    supported_mime_types: Set[str] = field(default_factory=lambda: {
        "image/png", "image/jpeg", "image/webp", "image/gif"
    })

    # TradingView URL patterns (don't download these)
    tradingview_patterns: List[str] = field(default_factory=lambda: [
        "tradingview.com",
        "tradingview.net",
        "tv.com",
    ])

    # Extraction timeout
    extraction_timeout_s: int = 30

    # Minimum image size in bytes
    min_image_size_bytes: int = 100
