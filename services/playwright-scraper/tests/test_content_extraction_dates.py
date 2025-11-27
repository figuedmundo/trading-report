"""Tests for Spanish date parsing."""

import pytest
import pytz
from datetime import datetime
from src.content_extraction.date_parser import parse_spanish_date


class TestSpanishDateParsing:
    """Test Spanish date parsing to UTC."""

    def test_parse_valid_spanish_date(self):
        """Verify valid Spanish date format parses correctly."""
        date_string = "26 de noviembre de 2025 a las 15:44"

        result = parse_spanish_date(date_string)

        assert result is not None
        # Result should be in UTC
        assert result.tzinfo == pytz.utc
        # Date components should match
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 26
        # Time should be converted (Europe/Madrid is UTC+1 in November)
        assert result.hour >= 14  # Converted from 15:44 Madrid time

    def test_parse_spanish_date_with_all_months(self):
        """Verify all Spanish month names are recognized."""
        months_and_numbers = [
            ("enero", 1), ("febrero", 2), ("marzo", 3), ("abril", 4),
            ("mayo", 5), ("junio", 6), ("julio", 7), ("agosto", 8),
            ("septiembre", 9), ("octubre", 10), ("noviembre", 11), ("diciembre", 12)
        ]

        for month_name, expected_month in months_and_numbers:
            date_string = f"15 de {month_name} de 2025 a las 12:00"
            result = parse_spanish_date(date_string)

            assert result is not None
            assert result.month == expected_month

    def test_parse_date_end_of_month(self):
        """Verify end-of-month dates parse correctly."""
        result = parse_spanish_date("31 de diciembre de 2025 a las 23:59")

        assert result is not None
        assert result.day == 31
        assert result.month == 12
        assert result.year == 2025

    def test_parse_leap_year_date(self):
        """Verify leap year dates parse correctly."""
        result = parse_spanish_date("29 de febrero de 2024 a las 12:00")

        assert result is not None
        assert result.day == 29
        assert result.month == 2
        assert result.year == 2024

    def test_return_none_for_invalid_format(self):
        """Verify invalid date format returns None."""
        invalid_dates = [
            "26/11/2025 15:44",  # Wrong format
            "2025-11-26 15:44",  # ISO format
            "invalid date",      # Garbage
            "",                  # Empty
            None,                # None
        ]

        for date_string in invalid_dates:
            result = parse_spanish_date(date_string)

            assert result is None

    def test_return_none_for_invalid_month_name(self):
        """Verify invalid month names return None."""
        date_string = "26 de invalidmonth de 2025 a las 15:44"

        result = parse_spanish_date(date_string)

        assert result is None

    def test_return_none_for_invalid_date_values(self):
        """Verify invalid date values return None."""
        # February 30th doesn't exist
        result = parse_spanish_date("30 de febrero de 2025 a las 15:44")

        assert result is None

    def test_timezone_conversion_to_utc(self):
        """Verify dates are converted to UTC."""
        date_string = "26 de noviembre de 2025 a las 12:00"

        result = parse_spanish_date(date_string)

        assert result is not None
        assert result.tzinfo == pytz.utc
