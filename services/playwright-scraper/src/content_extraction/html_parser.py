"""HTML parsing and semantic tag filtering."""

import logging
import re
from typing import Optional, List, Tuple
from bs4 import BeautifulSoup, NavigableString
from src.content_extraction.config import ExtractionConfig

logger = logging.getLogger(__name__)


def extract_semantic_html(
    html: str,
    config: Optional[ExtractionConfig] = None
) -> Optional[str]:
    """
    Extract clean semantic HTML from raw HTML content.

    Removes non-semantic tags (script, style, meta, link), filters elements
    via CSS selectors, and preserves only allowed tags with safe attributes.

    Args:
        html: Raw HTML content
        config: Extraction configuration (uses default if None)

    Returns:
        Clean semantic HTML string, or None on error
    """
    if not html or not isinstance(html, str):
        return None

    config = config or ExtractionConfig()

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove elements matching filter selectors
        for selector in config.filter_selectors:
            for element in soup.select(selector):
                element.decompose()

        # Extract only allowed tags
        for tag in soup.find_all(True):  # True = all tags
            if tag.name not in config.allowed_html_tags:
                # Keep text content, remove tag
                tag.unwrap()

        # Clean attributes from tags, keep only safe ones
        for tag in soup.find_all(True):
            if tag.name == "a":
                # Keep href for links
                href = tag.get("href")
                tag.attrs.clear()
                if href:
                    tag.attrs["href"] = href
            elif tag.name == "img":
                # Keep src, alt, width, height for images
                attrs_to_keep = {}
                for attr in ["src", "alt", "width", "height"]:
                    value = tag.get(attr)
                    if value:
                        attrs_to_keep[attr] = value
                tag.attrs.clear()
                tag.attrs.update(attrs_to_keep)
            else:
                # Remove all attributes from other tags
                tag.attrs.clear()

        # Normalize whitespace
        html_string = str(soup)
        html_string = normalize_whitespace(html_string)

        return html_string if html_string.strip() else None

    except Exception as e:
        logger.error(f"Error extracting semantic HTML: {e}")
        return None


def extract_with_fallback(html: str, article_html: str) -> Tuple[str, Optional[str]]:
    """
    Extract content with graceful fallback cascade.

    Primary: semantic HTML → Fallback 1: plain text → Fallback 2: raw HTML

    Args:
        html: Full page HTML
        article_html: Article content HTML (from CSS selector)

    Returns:
        Tuple of (extracted_text, fallback_used)
        fallback_used is None | "plain_text" | "raw_html"
    """
    # Try primary: semantic HTML extraction
    try:
        semantic_html = extract_semantic_html(article_html)
        if semantic_html and semantic_html.strip():
            return (semantic_html, None)
    except Exception as e:
        logger.warning(f"Semantic HTML extraction failed: {e}")

    # Fallback 1: plain text extraction
    try:
        plain_text = extract_plain_text(article_html)
        if plain_text and plain_text.strip():
            logger.warning("Fell back to plain text extraction")
            return (plain_text, "plain_text")
    except Exception as e:
        logger.warning(f"Plain text extraction failed: {e}")

    # Fallback 2: raw HTML
    if article_html and article_html.strip():
        logger.warning("Fell back to raw HTML storage")
        return (article_html, "raw_html")

    # Should never reach here - always return something
    return ("", "raw_html")


def extract_plain_text(html: str) -> Optional[str]:
    """
    Extract plain text from HTML by stripping all tags.

    Args:
        html: HTML content

    Returns:
        Plain text with no HTML tags
    """
    if not html:
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
        # Get text and normalize whitespace
        text = soup.get_text(separator="\n")
        return normalize_whitespace(text)
    except Exception as e:
        logger.error(f"Error extracting plain text: {e}")
        return None


def extract_element_text(
    html: str,
    selector: str,
    config: Optional[ExtractionConfig] = None
) -> Optional[str]:
    """
    Extract text content from specific CSS selector.

    Args:
        html: HTML content
        selector: CSS selector
        config: Extraction configuration

    Returns:
        Text content or None if not found
    """
    if not html or not selector:
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
        element = soup.select_one(selector)

        if element:
            text = element.get_text(strip=True)
            # Normalize whitespace in extracted text
            text = normalize_whitespace(text)
            return text if text else None

        logger.debug(f"CSS selector did not match: {selector}")
        return None

    except Exception as e:
        logger.warning(f"Error extracting element text for selector '{selector}': {e}")
        return None


def extract_article_content(
    html: str,
    config: Optional[ExtractionConfig] = None
) -> Optional[str]:
    """
    Extract article content using CSS selector.

    Args:
        html: Page HTML
        config: Extraction configuration

    Returns:
        Inner HTML of article content, or None if not found
    """
    if not html:
        return None

    config = config or ExtractionConfig()

    try:
        soup = BeautifulSoup(html, "html.parser")
        article = soup.select_one(config.article_selector)

        if article:
            return str(article)

        logger.warning(f"Article selector did not match: {config.article_selector}")
        return None

    except Exception as e:
        logger.error(f"Error extracting article content: {e}")
        return None


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text/HTML.

    Collapses multiple spaces/newlines, strips leading/trailing whitespace.

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # Replace multiple whitespace sequences with single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading and trailing whitespace
    text = text.strip()
    return text
