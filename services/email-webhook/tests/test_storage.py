"""
Tests for Task Group 7: PostgreSQL Integration & Report Insertion
"""

import pytest
import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from storage import insert_report, calculate_payload_hash


class TestReportInsertion:
    """Test report insertion into database."""

    @patch("storage.get_db_pool")
    def test_new_report_inserted_successfully(self, mock_get_pool):
        """Test that new report is inserted and report_id returned."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_get_pool.return_value = mock_pool
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("123e4567-e89b-12d3-a456-426614174000",)

        success, report_id = insert_report(
            email_from="sender@example.com",
            email_subject="Trading Report",
            email_message_id="<msg-123@example.com>",
            email_received_at="2025-11-25T10:00:00Z",
            report_url="https://example.com/report",
            metadata={"keywords": ["trading"]},
        )

        assert success is True
        assert report_id is not None

    @patch("storage.get_db_pool")
    def test_duplicate_email_returns_existing_id(self, mock_get_pool):
        """Test that duplicate email_message_id returns existing report_id."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_get_pool.return_value = mock_pool
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Simulate UNIQUE constraint violation
        error = Exception("UNIQUE constraint violation")
        mock_cursor.execute.side_effect = [error, None]
        mock_cursor.fetchone.return_value = ("existing-id-123",)

        success, report_id = insert_report(
            email_from="sender@example.com",
            email_subject="Trading Report",
            email_message_id="<msg-123@example.com>",
            email_received_at="2025-11-25T10:00:00Z",
            report_url="https://example.com/report",
            metadata={},
        )

        assert success is True
        assert report_id is not None

    @patch("storage.get_db_pool")
    def test_report_url_can_be_none(self, mock_get_pool):
        """Test that report_url can be NULL."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_get_pool.return_value = mock_pool
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("report-id-123",)

        success, report_id = insert_report(
            email_from="sender@example.com",
            email_subject="Report",
            email_message_id="<msg@example.com>",
            email_received_at="2025-11-25T10:00:00Z",
            report_url=None,  # No URL found
            metadata={},
        )

        assert success is True

    def test_payload_hash_generation(self):
        """Test SHA256 hash of JSON payload."""
        payload = '{"from":"test@example.com","subject":"Report"}'
        hash_value = calculate_payload_hash(payload)

        assert len(hash_value) == 64  # SHA256 hex is 64 chars
        assert hash_value.isalnum()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
