"""
Email header and body parsing utilities.

Extracts and normalizes email headers (From, Subject, Message-ID, Date)
and handles multipart MIME structures (plain text and HTML).
"""

import re
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional, Tuple, Dict, Any
from html import unescape
import html2text

logger = logging.getLogger(__name__)


def parse_email_headers(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract and normalize email headers from webhook payload.

    Extracts required headers (From, Subject, Message-ID, Date) and optional
    headers (To, Cc, Reply-To).

    Args:
        payload: Email provider's webhook payload

    Returns:
        Dictionary with extracted headers
    """
    headers = {}

    # Extract required headers
    # From field may be under 'from' or 'from_' depending on JSON parsing
    email_from = payload.get("from") or payload.get("from_")
    if email_from:
        headers["email_from"] = email_from.strip().lower()
    else:
        raise ValueError("Missing 'from' field in payload")

    subject = payload.get("subject")
    if subject:
        headers["email_subject"] = subject.strip()
    else:
        raise ValueError("Missing 'subject' field in payload")

    # Message-ID field (may be 'message-id', 'message_id', or 'message_id')
    message_id = (
        payload.get("message-id")
        or payload.get("message_id")
        or payload.get("message_id_alias")
    )
    if message_id:
        headers["email_message_id"] = message_id.strip()
    else:
        raise ValueError("Missing 'message-id' or 'message_id' field in payload")

    # Timestamp field (may be 'timestamp' or other variations)
    timestamp_str = payload.get("timestamp")
    if timestamp_str:
        headers["email_timestamp"] = timestamp_str.strip()
        # Parse to ISO 8601
        try:
            timestamp = parsedate_to_datetime(timestamp_str)
            headers["email_received_at"] = timestamp.isoformat().replace("+00:00", "Z")
        except Exception as e:
            logger.warning(f"Failed to parse timestamp {timestamp_str}: {e}")
            # Fallback to string
            headers["email_received_at"] = timestamp_str
    else:
        raise ValueError("Missing 'timestamp' field in payload")

    # Extract optional headers
    email_to = payload.get("to")
    if email_to:
        headers["email_to"] = email_to.strip()

    email_cc = payload.get("cc")
    if email_cc:
        headers["email_cc"] = email_cc.strip()

    reply_to = payload.get("reply-to") or payload.get("reply_to")
    if reply_to:
        headers["email_reply_to"] = reply_to.strip()

    return headers


def extract_email_body(payload: Dict[str, Any]) -> str:
    """
    Extract email body text from webhook payload.

    Prefers plain text over HTML. Handles both 'text' and 'stripped_text' fields.

    Args:
        payload: Email provider's webhook payload

    Returns:
        Email body text content
    """
    # Try plain text first (includes both 'text' and 'stripped_text')
    # Also handle 'stripped-text' variant
    text_content = (
        payload.get("stripped_text")
        or payload.get("stripped-text")
        or payload.get("text")
    )

    if text_content:
        return text_content.strip()

    # Fall back to HTML if no plain text available
    html_content = payload.get("html")
    if html_content:
        return convert_html_to_text(html_content)

    return ""


def convert_html_to_text(html_content: str) -> str:
    """
    Convert HTML to plain text.

    Uses html2text library for better formatting than basic tag stripping.

    Args:
        html_content: HTML content as string

    Returns:
        Plain text representation
    """
    try:
        # Use html2text for better conversion
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        text = h.handle(html_content)
        return text.strip()
    except Exception as e:
        logger.warning(f"html2text conversion failed: {e}, using basic stripping")
        return strip_html_tags(html_content)


def strip_html_tags(html_content: str) -> str:
    """
    Basic HTML tag stripping (fallback method).

    Removes <script>, <style>, and other HTML tags.

    Args:
        html_content: HTML content as string

    Returns:
        Text with tags removed
    """
    # Remove script and style elements
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = unescape(text)

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def validate_email_payload(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate that payload contains all required fields for email parsing.

    Args:
        payload: Email provider's webhook payload

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["from", "subject", "timestamp", "message-id", "message_id"]

    # Check for required fields
    has_from = payload.get("from") or payload.get("from_")
    has_subject = payload.get("subject")
    has_timestamp = payload.get("timestamp")
    has_message_id = (
        payload.get("message-id")
        or payload.get("message_id")
        or payload.get("message_id_alias")
    )

    if not has_from:
        return False, "Missing required field: 'from'"

    if not has_subject:
        return False, "Missing required field: 'subject'"

    if not has_timestamp:
        return False, "Missing required field: 'timestamp'"

    if not has_message_id:
        return False, "Missing required field: 'message-id' or 'message_id'"

    # Check for body content (at least one of text formats)
    has_text = (
        payload.get("text")
        or payload.get("stripped_text")
        or payload.get("stripped-text")
    )
    has_html = payload.get("html")

    if not has_text and not has_html:
        return False, "Missing email body: no 'text', 'stripped_text', 'stripped-text', or 'html' field"

    return True, None
