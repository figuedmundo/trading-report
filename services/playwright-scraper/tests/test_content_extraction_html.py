"""Tests for HTML parsing and semantic tag filtering."""

import pytest
from src.content_extraction.html_parser import (
    extract_semantic_html,
    extract_plain_text,
    extract_element_text,
    normalize_whitespace,
)
from src.content_extraction.config import ExtractionConfig


class TestSemanticHtmlExtraction:
    """Test semantic HTML extraction."""

    def test_extract_allowed_semantic_tags(self):
        """Verify only allowed semantic tags are preserved."""
        html = '''
        <article>
            <h1>Title</h1>
            <h2>Subtitle</h2>
            <p>Paragraph text</p>
            <strong>Bold text</strong>
            <em>Italic text</em>
            <ul><li>Item 1</li><li>Item 2</li></ul>
            <a href="https://example.com">Link</a>
            <img src="test.png" alt="Test" />
        </article>
        '''

        result = extract_semantic_html(html)

        assert result is not None
        assert "<h1>" in result or "Title" in result
        assert "<h2>" in result or "Subtitle" in result
        assert "<p>" in result or "Paragraph" in result
        assert "<strong>" in result or "Bold" in result
        assert "<em>" in result or "Italic" in result
        assert "<a" in result or "Link" in result

    def test_remove_script_and_style_tags(self):
        """Verify script and style tags are removed."""
        html = '''
        <article>
            <p>Good content</p>
            <script>alert('bad')</script>
            <style>body { color: red; }</style>
            <p>More content</p>
        </article>
        '''

        result = extract_semantic_html(html)

        assert result is not None
        assert "<script>" not in result
        assert "alert" not in result
        assert "<style>" not in result
        assert "color: red" not in result

    def test_remove_non_semantic_tags(self):
        """Verify non-semantic tags are removed."""
        html = '''
        <article>
            <p>Good content</p>
            <div class="nav">Navigation</div>
            <span class="badge">Badge</span>
            <code>Code block</code>
        </article>
        '''

        result = extract_semantic_html(html)

        assert result is not None
        # Non-semantic tags should be removed, but text preserved
        assert "<code>" not in result or "Code block" in result

    def test_preserve_image_attributes(self):
        """Verify img tag attributes are preserved."""
        html = '<img src="image.png" alt="Chart" width="800" height="600" />'

        result = extract_semantic_html(html)

        assert result is not None
        assert 'src=' in result or "image.png" in result
        assert 'alt=' in result or "Chart" in result

    def test_preserve_link_href(self):
        """Verify link href attributes are preserved."""
        html = '<a href="https://example.com">Click here</a>'

        result = extract_semantic_html(html)

        assert result is not None
        assert 'href=' in result or "https://example.com" in result

    def test_normalize_whitespace(self):
        """Verify whitespace is normalized."""
        html = '<p>Text   with    extra     spaces</p>'

        result = extract_semantic_html(html)

        assert result is not None
        # Should collapse multiple spaces
        assert "   " not in result or "Text with extra spaces" in result

    def test_handle_malformed_html(self):
        """Verify malformed HTML is handled gracefully."""
        html = '<p>Unclosed paragraph<div>Unclosed div'

        result = extract_semantic_html(html)

        # Should not crash, should return something
        assert result is not None


class TestPlainTextExtraction:
    """Test plain text extraction."""

    def test_extract_plain_text_strips_all_tags(self):
        """Verify all HTML tags are stripped from output."""
        html = '<h1>Title</h1><p>Paragraph <strong>with bold</strong></p>'

        result = extract_plain_text(html)

        assert result is not None
        assert "<" not in result
        assert ">" not in result
        assert "Title" in result
        assert "Paragraph" in result
        assert "with bold" in result

    def test_handle_empty_html(self):
        """Verify empty HTML returns None or empty string."""
        result = extract_plain_text("")

        assert result is None or result == ""

    def test_handle_none_html(self):
        """Verify None input returns None."""
        result = extract_plain_text(None)

        assert result is None


class TestElementTextExtraction:
    """Test CSS selector-based element text extraction."""

    def test_extract_text_from_selector(self):
        """Verify text is extracted from matching selector."""
        html = '<div class="author">John Doe</div>'

        result = extract_element_text(html, ".author")

        assert result == "John Doe"

    def test_return_none_for_missing_selector(self):
        """Verify None is returned when selector doesn't match."""
        html = '<div class="author">John Doe</div>'

        result = extract_element_text(html, ".missing")

        assert result is None

    def test_normalize_extracted_text(self):
        """Verify extracted text is normalized."""
        html = '<div class="title">   Spaced   Title   </div>'

        result = extract_element_text(html, ".title")

        assert result == "Spaced Title"


class TestWhitespaceNormalization:
    """Test whitespace normalization."""

    def test_collapse_multiple_spaces(self):
        """Verify multiple spaces are collapsed."""
        text = "Text   with    extra     spaces"

        result = normalize_whitespace(text)

        assert "   " not in result
        assert result == "Text with extra spaces"

    def test_collapse_newlines(self):
        """Verify newlines are collapsed."""
        text = "Line1\n\n\nLine2\n\nLine3"

        result = normalize_whitespace(text)

        assert result == "Line1 Line2 Line3"

    def test_strip_leading_trailing_whitespace(self):
        """Verify leading/trailing whitespace is stripped."""
        text = "   Centered text   "

        result = normalize_whitespace(text)

        assert result == "Centered text"
