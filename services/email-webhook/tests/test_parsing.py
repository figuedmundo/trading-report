"""
Tests for Task Group 4: Request Parsing & Pydantic Validation

Tests request parsing, header extraction, and multipart MIME handling.
"""

import pytest
import sys
import os
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parsers import (
    parse_email_headers,
    extract_email_body,
    strip_html_tags,
    validate_email_payload,
)


class TestEmailHeaderExtraction:
    """Test email header extraction from webhook payloads."""

    def test_required_headers_extracted(self):
        """Test that all required headers are extracted."""
        payload = {
            "from": "sender@example.com",
            "subject": "Trading Report Analysis",
            "message-id": "<msg-id-123@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
            "text": "Report content here",
        }

        headers = parse_email_headers(payload)

        assert headers["email_from"] == "sender@example.com"
        assert headers["email_subject"] == "Trading Report Analysis"
        assert headers["email_message_id"] == "<msg-id-123@example.com>"
        assert "email_received_at" in headers

    def test_optional_headers_extracted(self):
        """Test that optional headers are extracted when present."""
        payload = {
            "from": "sender@example.com",
            "subject": "Trading Report",
            "message-id": "<msg-id@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
            "text": "Content",
            "to": "recipient@example.com",
            "cc": "cc@example.com",
            "reply-to": "reply@example.com",
        }

        headers = parse_email_headers(payload)

        assert headers["email_to"] == "recipient@example.com"
        assert headers["email_cc"] == "cc@example.com"
        assert headers["email_reply_to"] == "reply@example.com"

    def test_email_from_normalized_to_lowercase(self):
        """Test that email address is normalized to lowercase."""
        payload = {
            "from": "Sender@EXAMPLE.COM",
            "subject": "Report",
            "message-id": "<msg-id@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
            "text": "Content",
        }

        headers = parse_email_headers(payload)

        assert headers["email_from"] == "sender@example.com"

    def test_timestamp_converted_to_iso8601(self):
        """Test that RFC 2822 timestamp is converted to ISO 8601."""
        payload = {
            "from": "sender@example.com",
            "subject": "Report",
            "message-id": "<msg-id@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
            "text": "Content",
        }

        headers = parse_email_headers(payload)

        # Should contain ISO 8601 format with Z suffix
        assert "email_received_at" in headers
        assert "T" in headers["email_received_at"]
        assert "Z" in headers["email_received_at"] or "+00:00" in headers["email_received_at"]

    def test_missing_from_raises_error(self):
        """Test that missing 'from' field raises ValueError."""
        payload = {
            "subject": "Report",
            "message-id": "<msg-id@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
            "text": "Content",
        }

        with pytest.raises(ValueError, match="Missing.*from"):
            parse_email_headers(payload)

    def test_missing_subject_raises_error(self):
        """Test that missing 'subject' field raises ValueError."""
        payload = {
            "from": "sender@example.com",
            "message-id": "<msg-id@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
            "text": "Content",
        }

        with pytest.raises(ValueError, match="Missing.*subject"):
            parse_email_headers(payload)

    def test_missing_message_id_raises_error(self):
        """Test that missing 'message-id' field raises ValueError."""
        payload = {
            "from": "sender@example.com",
            "subject": "Report",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
            "text": "Content",
        }

        with pytest.raises(ValueError, match="Missing.*message"):
            parse_email_headers(payload)

    def test_message_id_underscore_variant_accepted(self):
        """Test that 'message_id' variant is accepted."""
        payload = {
            "from": "sender@example.com",
            "subject": "Report",
            "message_id": "msg-id-123",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
            "text": "Content",
        }

        headers = parse_email_headers(payload)

        assert headers["email_message_id"] == "msg-id-123"


class TestEmailBodyExtraction:
    """Test email body extraction from webhook payloads."""

    def test_plain_text_extracted(self):
        """Test that plain text body is extracted."""
        payload = {
            "from": "sender@example.com",
            "subject": "Report",
            "message-id": "<msg-id@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
            "text": "This is the email body content.",
        }

        body = extract_email_body(payload)

        assert body == "This is the email body content."

    def test_stripped_text_preferred_over_text(self):
        """Test that 'stripped_text' is preferred over 'text'."""
        payload = {
            "text": "Original text with formatting",
            "stripped_text": "Cleaned text without formatting",
        }

        body = extract_email_body(payload)

        assert body == "Cleaned text without formatting"

    def test_html_converted_to_text_when_no_plain_text(self):
        """Test that HTML is converted to text when plain text not available."""
        payload = {
            "html": "<p>This is HTML content</p><p>With multiple paragraphs</p>",
        }

        body = extract_email_body(payload)

        # Should contain the text content without HTML tags
        assert "HTML content" in body or "This is HTML content" in body
        assert "<p>" not in body

    def test_html_tags_stripped_from_content(self):
        """Test that HTML tags are properly stripped."""
        html = "<div class='content'><p>Hello <b>World</b></p></div>"

        text = strip_html_tags(html)

        assert "<" not in text
        assert ">" not in text
        assert "Hello" in text
        assert "World" in text

    def test_script_tags_removed_from_html(self):
        """Test that script tags are removed from HTML."""
        html = "<p>Content</p><script>malicious code</script><p>More</p>"

        text = strip_html_tags(html)

        assert "malicious" not in text
        assert "script" not in text
        assert "Content" in text
        assert "More" in text

    def test_empty_body_returned_when_no_content(self):
        """Test that empty string is returned when no body content available."""
        payload = {
            "from": "sender@example.com",
        }

        body = extract_email_body(payload)

        assert body == ""


class TestPayloadValidation:
    """Test webhook payload validation."""

    def test_valid_mailgun_payload_accepted(self):
        """Test that valid Mailgun-format payload is accepted."""
        payload = {
            "from": "sender@example.com",
            "subject": "Trading Report",
            "stripped-text": "Report content",
            "message-id": "<msg-id@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
        }

        is_valid, error = validate_email_payload(payload)

        assert is_valid is True
        assert error is None

    def test_valid_sendgrid_payload_accepted(self):
        """Test that valid SendGrid-format payload is accepted."""
        payload = {
            "from": "sender@example.com",
            "subject": "Trading Report",
            "text": "Report content",
            "message_id": "msg-id-123",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
        }

        is_valid, error = validate_email_payload(payload)

        assert is_valid is True
        assert error is None

    def test_missing_from_rejected(self):
        """Test that missing 'from' field is rejected."""
        payload = {
            "subject": "Report",
            "text": "Content",
            "message-id": "<msg-id@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
        }

        is_valid, error = validate_email_payload(payload)

        assert is_valid is False
        assert "from" in error.lower()

    def test_missing_subject_rejected(self):
        """Test that missing 'subject' field is rejected."""
        payload = {
            "from": "sender@example.com",
            "text": "Content",
            "message-id": "<msg-id@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
        }

        is_valid, error = validate_email_payload(payload)

        assert is_valid is False
        assert "subject" in error.lower()

    def test_missing_body_rejected(self):
        """Test that missing email body is rejected."""
        payload = {
            "from": "sender@example.com",
            "subject": "Report",
            "message-id": "<msg-id@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
        }

        is_valid, error = validate_email_payload(payload)

        assert is_valid is False
        assert "body" in error.lower() or "text" in error.lower()

    def test_html_only_body_accepted(self):
        """Test that HTML-only body content is accepted."""
        payload = {
            "from": "sender@example.com",
            "subject": "Report",
            "html": "<p>Content</p>",
            "message-id": "<msg-id@example.com>",
            "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
        }

        is_valid, error = validate_email_payload(payload)

        assert is_valid is True
        assert error is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
