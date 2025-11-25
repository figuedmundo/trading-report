"""
Tests for Task Group 10: Response Format & Correlation
"""

import pytest
import sys
import os
import json
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models import WebhookSuccessResponse, WebhookErrorResponse


class TestResponseFormat:
    """Test standardized response format."""

    def test_success_response_201_created(self):
        """Test 201 Created response format."""
        response = WebhookSuccessResponse(
            status="created",
            report_id="123e4567-e89b-12d3-a456-426614174000",
            correlation_id="456f7890-abcd-ef12-3456-789012345678",
            message="Email processed successfully",
            timestamp="2025-11-25T10:00:00Z",
        )

        assert response.success is True
        assert response.status == "created"
        assert response.report_id is not None
        assert response.correlation_id is not None
        assert response.timestamp.endswith("Z")

    def test_success_response_202_accepted(self):
        """Test 202 Accepted response format."""
        response = WebhookSuccessResponse(
            status="accepted",
            report_id="123e4567-e89b-12d3-a456-426614174000",
            correlation_id="456f7890-abcd-ef12-3456-789012345678",
            message="Email processed successfully",
            timestamp="2025-11-25T10:00:00Z",
        )

        assert response.success is True
        assert response.status == "accepted"

    def test_error_response_format(self):
        """Test error response format."""
        response = WebhookErrorResponse(
            status="rejected",
            error="Invalid signature",
            correlation_id="456f7890-abcd-ef12-3456-789012345678",
            timestamp="2025-11-25T10:00:00Z",
        )

        assert response.success is False
        assert response.status == "rejected"
        assert response.error is not None
        assert response.correlation_id is not None

    def test_correlation_id_included_in_all_responses(self):
        """Test that correlation_id is present in all responses."""
        correlation_id = "456f7890-abcd-ef12-3456-789012345678"

        success_response = WebhookSuccessResponse(
            status="created",
            report_id="123",
            correlation_id=correlation_id,
            message="Success",
            timestamp="2025-11-25T10:00:00Z",
        )

        error_response = WebhookErrorResponse(
            status="rejected",
            error="Error",
            correlation_id=correlation_id,
            timestamp="2025-11-25T10:00:00Z",
        )

        assert success_response.correlation_id == correlation_id
        assert error_response.correlation_id == correlation_id

    def test_timestamp_iso8601_format(self):
        """Test that timestamps are in ISO 8601 format."""
        timestamp = "2025-11-25T10:30:45Z"

        response = WebhookSuccessResponse(
            status="created",
            report_id="123",
            correlation_id="456",
            message="Success",
            timestamp=timestamp,
        )

        # Should parse without error as ISO 8601
        assert "T" in response.timestamp
        assert response.timestamp.endswith("Z")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
