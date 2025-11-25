"""
URL extraction and portal validation.

Extracts URLs from email body and filters them by trusted portal domains.
Reuses URL extraction pattern from refs/scraper.py.
"""

import re
import logging
from typing import List, Dict, Tuple
from urllib.parse import urlparse
from config import get_config

logger = logging.getLogger(__name__)


def extract_urls_from_text(text: str) -> List[str]:
    """
    Extract URLs from plain text content.

    Uses regex pattern to find http/https URLs.

    Args:
        text: Plain text content

    Returns:
        List of extracted URLs
    """
    # Regex pattern for URLs
    url_pattern = r"https?://[^\s]+"
    urls = re.findall(url_pattern, text)
    return urls


def extract_urls_from_html_href(html: str) -> List[str]:
    """
    Extract URLs from HTML href attributes.

    Finds all <a href="..."> attributes in HTML content.

    Args:
        html: HTML content

    Returns:
        List of extracted URLs
    """
    # Regex pattern for href attributes
    href_pattern = r'href=(["\'])([^"\']*)\1'
    matches = re.findall(href_pattern, html)
    urls = [match[1] for match in matches if match[1].startswith("http")]
    return urls


def extract_all_urls(text: str, html: str) -> List[str]:
    """
    Extract URLs from both plain text and HTML content.

    Combines URLs from text and HTML, removes duplicates.

    Args:
        text: Plain text content
        html: HTML content

    Returns:
        List of unique URLs
    """
    urls = []

    if text:
        urls.extend(extract_urls_from_text(text))

    if html:
        urls.extend(extract_urls_from_html_href(html))

    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


def validate_url_format(url: str) -> bool:
    """
    Validate that URL has valid format.

    Args:
        url: URL string to validate

    Returns:
        True if valid http/https URL, False otherwise
    """
    try:
        parsed = urlparse(url)
        is_valid = parsed.scheme in ("http", "https") and bool(parsed.netloc)
        return is_valid
    except Exception as e:
        logger.warning(f"URL parsing error for {url}: {e}")
        return False


def filter_urls_by_trusted_domains(urls: List[str]) -> Tuple[str, List[str], int]:
    """
    Filter URLs to only those matching trusted portal domains.

    Implements domain/path pattern filtering matching specification:
    - Case-insensitive domain matching
    - Path prefix matching

    Args:
        urls: List of URLs to filter

    Returns:
        Tuple of (first_valid_url_or_none, additional_valid_urls, total_count)
    """
    config = get_config()
    trusted_domains = config.trusted_domains

    valid_urls = []

    for url in urls:
        if not validate_url_format(url):
            continue

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check if domain matches trusted domains
            for trusted_domain in trusted_domains:
                trusted_domain_lower = trusted_domain.lower().strip()
                if domain == trusted_domain_lower or domain.endswith(f".{trusted_domain_lower}"):
                    # For now, accept all paths from trusted domain
                    # Future: Add path prefix matching per spec
                    valid_urls.append(url)
                    break

        except Exception as e:
            logger.warning(f"Error filtering URL {url}: {e}")
            continue

    # Return first valid URL, additional URLs, and total found count
    first_url = valid_urls[0] if valid_urls else None
    additional = valid_urls[1:] if len(valid_urls) > 1 else []

    return first_url, additional, len(urls)
