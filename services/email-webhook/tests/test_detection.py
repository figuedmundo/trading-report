"""
Tests for Task Group 5: Keyword-Based Report Detection
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from detection import detect_trading_report


class TestKeywordDetection:
    """Test keyword-based report detection."""

    def test_keyword_match_in_subject(self):
        """Test keyword match found in subject line."""
        with patch("detection.get_config") as mock_config:
            config = MagicMock()
            config.report_keywords = ["trading report", "analysis"]
            mock_config.return_value = config

            is_detected, matched = detect_trading_report(
                "Trading Report for Nov 25",
                "Portfolio analysis"
            )

            assert is_detected is True
            assert len(matched) > 0

    def test_keyword_match_in_body(self):
        """Test keyword match found in body text."""
        with patch("detection.get_config") as mock_config:
            config = MagicMock()
            config.report_keywords = ["trading report"]
            mock_config.return_value = config

            is_detected, matched = detect_trading_report(
                "Market Update",
                "This is a trading report with analysis."
            )

            assert is_detected is True

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive."""
        with patch("detection.get_config") as mock_config:
            config = MagicMock()
            config.report_keywords = ["Trading Report"]
            mock_config.return_value = config

            is_detected, matched = detect_trading_report(
                "TRADING REPORT FOR THIS WEEK",
                "Content here"
            )

            assert is_detected is True

    def test_no_keywords_found(self):
        """Test no keywords found scenario."""
        with patch("detection.get_config") as mock_config:
            config = MagicMock()
            config.report_keywords = ["trading report", "analysis"]
            mock_config.return_value = config

            is_detected, matched = detect_trading_report(
                "Regular Email",
                "Just some random content."
            )

            assert is_detected is False
            assert len(matched) == 0

    def test_multiple_keywords_matched(self):
        """Test matching multiple keywords."""
        with patch("detection.get_config") as mock_config:
            config = MagicMock()
            config.report_keywords = ["trading", "analysis", "recommendation"]
            mock_config.return_value = config

            is_detected, matched = detect_trading_report(
                "Trading analysis and recommendation",
                "Full trading report"
            )

            assert is_detected is True
            assert len(matched) >= 2

    def test_word_boundary_matching(self):
        """Test that keyword matching uses word boundaries."""
        with patch("detection.get_config") as mock_config:
            config = MagicMock()
            config.report_keywords = ["trade"]
            mock_config.return_value = config

            # "traded" should not match "trade" as a whole word
            is_detected, matched = detect_trading_report(
                "Subject",
                "This was traded yesterday"
            )

            # Should not match due to word boundary
            assert is_detected is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
