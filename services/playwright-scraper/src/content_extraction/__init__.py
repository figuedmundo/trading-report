"""Content extraction module for trading reports."""

from src.content_extraction.config import ExtractionConfig
from src.content_extraction.models import ExtractionResult
from src.content_extraction.extractor import ContentExtractor, extract_trading_report
from src.content_extraction.html_parser import (
    extract_semantic_html,
    extract_with_fallback,
    extract_plain_text,
    extract_element_text,
    extract_article_content,
)
from src.content_extraction.date_parser import parse_spanish_date
from src.content_extraction.image_handler import (
    is_tradingview_image,
    download_images_parallel,
)

__all__ = [
    "ExtractionConfig",
    "ExtractionResult",
    "ContentExtractor",
    "extract_trading_report",
    "extract_semantic_html",
    "extract_with_fallback",
    "extract_plain_text",
    "extract_element_text",
    "extract_article_content",
    "parse_spanish_date",
    "is_tradingview_image",
    "download_images_parallel",
]
