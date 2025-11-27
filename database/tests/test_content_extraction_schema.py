"""Tests for content extraction schema migration."""

import pytest
import json
from datetime import datetime, timezone


class TestContentExtractionSchema:
    """Test content extraction database schema additions."""

    def test_extracted_text_column_exists(self, db_connection):
        """Verify extracted_text column exists on reports table."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'reports' AND column_name = 'extracted_text'
        """)
        result = cursor.fetchone()
        cursor.close()

        assert result is not None
        assert result[0] == "extracted_text"
        assert result[1] == "text"

    def test_extracted_images_column_exists_with_default(self, db_connection):
        """Verify extracted_images JSONB column exists with default empty array."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'reports' AND column_name = 'extracted_images'
        """)
        result = cursor.fetchone()
        cursor.close()

        assert result is not None
        assert result[0] == "extracted_images"
        assert result[1] == "jsonb"
        assert "[]" in str(result[2])

    def test_insert_report_with_extracted_images_jsonb(self, db_connection):
        """Verify JSONB field accepts valid image metadata array."""
        cursor = db_connection.cursor()

        image_metadata = [
            {
                "url": "local://image-0",
                "content_type": "image/png",
                "position_index": 0,
                "base64_data": "iVBORw0KGgoAAAANS...",
                "is_tradingview": False,
                "width": 800,
                "height": 600,
                "download_status": "success"
            }
        ]

        cursor.execute("""
            INSERT INTO reports (
                email_received_at, email_from, email_subject, report_url,
                status, extracted_images
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, extracted_images
        """, (
            datetime.now(timezone.utc),
            "test@example.com",
            "Test Report",
            "https://example.com/report",
            "processing",
            json.dumps(image_metadata)
        ))

        result = cursor.fetchone()
        cursor.close()
        db_connection.commit()

        assert result is not None
        assert result[0] is not None  # ID
        assert result[1] == image_metadata  # JSONB parsed back

    def test_null_values_for_optional_extraction_fields(self, db_connection):
        """Verify extraction fields handle NULL values gracefully."""
        cursor = db_connection.cursor()

        cursor.execute("""
            INSERT INTO reports (
                email_received_at, email_from, email_subject, report_url,
                status
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, extracted_text, extracted_images
        """, (
            datetime.now(timezone.utc),
            "test@example.com",
            "Test",
            "https://example.com/report",
            "pending"
        ))

        result = cursor.fetchone()
        cursor.close()
        db_connection.commit()

        assert result is not None
        assert result[1] is None  # extracted_text is NULL
        assert result[2] == []    # extracted_images defaults to empty array
