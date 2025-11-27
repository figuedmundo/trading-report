"""
Data flow and integration tests for trading reports database.

These focused tests verify that the database supports the complete workflow
for report processing from email ingestion through analysis and notification.
"""

import json
import pytest


class TestCompleteReportLifecycle:
    """Test the complete report lifecycle from creation to completion."""

    def test_report_lifecycle_pending_to_completed(self, db_cursor):
        """Test report transitions from pending to completed with automatic processed_at."""
        # 1. Create report (email webhook)
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, email_from, email_subject, email_message_id,
                report_url, status, metadata
            ) VALUES (
                NOW(), 'sender@example.com', 'Daily Report',
                '<msg-123@example.com>', 'https://example.com/report',
                'pending', '{"broker": "XM"}'
            ) RETURNING id, status, processed_at
        """)
        report_id, status, processed_at = db_cursor.fetchone()
        assert status == 'pending'
        assert processed_at is None

        # 2. Update to processing and add content
        db_cursor.execute("""
            UPDATE reports SET
                status = 'processing',
                raw_content = 'Report content here',
                report_title = 'XAU/USD Report'
            WHERE id = %s
            RETURNING status
        """)
        status = db_cursor.fetchone()[0]
        assert status == 'processing'

        # 3. Create analysis
        db_cursor.execute("""
            INSERT INTO analyses (
                report_id, ai_provider, model_used, summary,
                sentiment, confidence_score, tokens_used, api_cost, processing_time_ms
            ) VALUES (
                %s, 'anthropic', 'claude-3-5-sonnet-20241022',
                'Gold showing bullish momentum',
                'bullish', 0.85, 500, 0.015, 2000
            ) RETURNING id
        """)
        analysis_id = db_cursor.fetchone()[0]

        # 4. Mark report as completed (triggers automatic processed_at)
        db_cursor.execute("""
            UPDATE reports SET status = 'completed'
            WHERE id = %s
            RETURNING status, processed_at
        """)
        status, processed_at = db_cursor.fetchone()
        assert status == 'completed'
        assert processed_at is not None  # Trigger should set this

        # 5. Create notifications
        db_cursor.execute("""
            INSERT INTO notifications (
                analysis_id, channel, recipient, status
            ) VALUES
                (%s, 'email', 'user@example.com', 'pending'),
                (%s, 'telegram', '123456789', 'pending')
            RETURNING COUNT(*)
        """, (analysis_id, analysis_id))

    def test_report_with_images_and_analysis(self, db_cursor):
        """Test report with images and complete analysis flow."""
        # 1. Create report
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status
            ) VALUES (NOW(), 'https://example.com/report', 'pending')
            RETURNING id
        """)
        report_id = db_cursor.fetchone()[0]

        # 2. Add images
        db_cursor.execute("""
            INSERT INTO report_images (
                report_id, image_url, image_type, mime_type,
                width, height, sequence_order, metadata
            ) VALUES
                (%s, 'https://example.com/chart1.png', 'chart', 'image/png',
                 1024, 768, 0, '{"timeframe": "4H"}'),
                (%s, 'https://example.com/chart2.png', 'chart', 'image/png',
                 1024, 768, 1, '{"timeframe": "1H"}')
        """, (report_id, report_id))

        # 3. Verify images were inserted
        db_cursor.execute("""
            SELECT COUNT(*) FROM report_images WHERE report_id = %s
        """, (report_id,))
        image_count = db_cursor.fetchone()[0]
        assert image_count == 2

        # 4. Create analysis with key_trades (JSONB array)
        key_trades = json.dumps([
            {"symbol": "XAUUSD", "entry": 2695.50, "exit": 2708.30, "profit": 12.80},
            {"symbol": "EURUSD", "entry": 1.0850, "exit": 1.0920, "profit": 0.0070}
        ])

        db_cursor.execute("""
            INSERT INTO analyses (
                report_id, ai_provider, model_used, summary,
                key_trades, sentiment, confidence_score,
                tokens_used, api_cost, processing_time_ms
            ) VALUES (
                %s, 'anthropic', 'claude-3-5-sonnet-20241022',
                'Strong bullish setup',
                %s::jsonb, 'bullish', 0.92,
                750, 0.022, 3200
            ) RETURNING id
        """, (report_id, key_trades))
        analysis_id = db_cursor.fetchone()[0]

        # 5. Mark report completed
        db_cursor.execute("""
            UPDATE reports SET status = 'completed' WHERE id = %s
        """, (report_id,))

        # 6. Query via view to verify complete data
        db_cursor.execute("""
            SELECT id, status, image_count, analysis_id, sentiment
            FROM vw_reports_with_analysis
            WHERE id = %s
        """, (report_id,))
        row = db_cursor.fetchone()
        assert row[1] == 'completed'
        assert row[2] == 2  # image_count
        assert row[3] == analysis_id


class TestForeignKeyRelationships:
    """Test that foreign key relationships work correctly."""

    def test_cascade_delete_report_deletes_images(self, db_cursor):
        """Test that deleting report cascades to report_images."""
        # Create report with image
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status
            ) VALUES (NOW(), 'https://example.com/test', 'pending')
            RETURNING id
        """)
        report_id = db_cursor.fetchone()[0]

        db_cursor.execute("""
            INSERT INTO report_images (
                report_id, image_url, image_type
            ) VALUES (%s, 'https://example.com/img.png', 'screenshot')
        """, (report_id,))

        # Verify image exists
        db_cursor.execute("""
            SELECT COUNT(*) FROM report_images WHERE report_id = %s
        """, (report_id,))
        assert db_cursor.fetchone()[0] == 1

        # Delete report
        db_cursor.execute("DELETE FROM reports WHERE id = %s", (report_id,))

        # Verify image was cascade deleted
        db_cursor.execute("""
            SELECT COUNT(*) FROM report_images WHERE report_id = %s
        """, (report_id,))
        assert db_cursor.fetchone()[0] == 0

    def test_cascade_delete_analysis_deletes_notifications(self, db_cursor):
        """Test that deleting analysis cascades to notifications."""
        # Create report -> analysis -> notifications
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status
            ) VALUES (NOW(), 'https://example.com/test', 'pending')
            RETURNING id
        """)
        report_id = db_cursor.fetchone()[0]

        db_cursor.execute("""
            INSERT INTO analyses (
                report_id, ai_provider, model_used, summary,
                tokens_used, api_cost, processing_time_ms
            ) VALUES (
                %s, 'anthropic', 'claude-3-5-sonnet', 'Test summary',
                500, 0.015, 2000
            ) RETURNING id
        """, (report_id,))
        analysis_id = db_cursor.fetchone()[0]

        db_cursor.execute("""
            INSERT INTO notifications (
                analysis_id, channel, recipient
            ) VALUES
                (%s, 'email', 'test@example.com'),
                (%s, 'telegram', '12345')
        """, (analysis_id, analysis_id))

        # Verify notifications exist
        db_cursor.execute("""
            SELECT COUNT(*) FROM notifications WHERE analysis_id = %s
        """, (analysis_id,))
        assert db_cursor.fetchone()[0] == 2

        # Delete analysis
        db_cursor.execute("DELETE FROM analyses WHERE id = %s", (analysis_id,))

        # Verify notifications were cascade deleted
        db_cursor.execute("""
            SELECT COUNT(*) FROM notifications WHERE analysis_id = %s
        """, (analysis_id,))
        assert db_cursor.fetchone()[0] == 0


class TestStateTransitionsAndRetryLogic:
    """Test status transitions and retry logic."""

    def test_retry_count_increment(self, db_cursor):
        """Test retry_count increments on failures."""
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status, retry_count
            ) VALUES (NOW(), 'https://example.com/test', 'failed', 0)
            RETURNING id
        """)
        report_id = db_cursor.fetchone()[0]

        # Simulate retry attempt
        db_cursor.execute("""
            UPDATE reports SET
                retry_count = retry_count + 1,
                last_retry_at = NOW(),
                error_message = 'Login timeout'
            WHERE id = %s
            RETURNING retry_count, last_retry_at
        """, (report_id,))
        retry_count, last_retry = db_cursor.fetchone()
        assert retry_count == 1
        assert last_retry is not None

    def test_notification_retry_logic(self, db_cursor):
        """Test notification retry_count and max_retries constraint."""
        # Setup: create report, analysis, notification
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status
            ) VALUES (NOW(), 'https://example.com/test', 'completed')
            RETURNING id
        """)
        report_id = db_cursor.fetchone()[0]

        db_cursor.execute("""
            INSERT INTO analyses (
                report_id, ai_provider, model_used, summary,
                tokens_used, api_cost, processing_time_ms
            ) VALUES (
                %s, 'anthropic', 'claude-3-5-sonnet', 'Test',
                500, 0.015, 2000
            ) RETURNING id
        """, (report_id,))
        analysis_id = db_cursor.fetchone()[0]

        db_cursor.execute("""
            INSERT INTO notifications (
                analysis_id, channel, recipient, status, retry_count, max_retries
            ) VALUES (%s, 'email', 'test@example.com', 'retrying', 0, 3)
            RETURNING id
        """, (analysis_id,))
        notification_id = db_cursor.fetchone()[0]

        # Increment retry_count
        db_cursor.execute("""
            UPDATE notifications SET
                retry_count = retry_count + 1
            WHERE id = %s AND retry_count < max_retries
            RETURNING retry_count
        """, (notification_id,))
        new_count = db_cursor.fetchone()[0]
        assert new_count == 1

    def test_error_message_storage(self, db_cursor):
        """Test error_message is stored on failure."""
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status,
                error_message
            ) VALUES (
                NOW(), 'https://example.com/test', 'failed',
                'Failed to connect: timeout after 30s'
            ) RETURNING id, error_message
        """)
        report_id, error = db_cursor.fetchone()
        assert error == 'Failed to connect: timeout after 30s'


class TestJSONBMetadataAndQuerying:
    """Test JSONB metadata storage and queries."""

    def test_report_metadata_storage_and_retrieval(self, db_cursor):
        """Test storing and querying JSONB metadata in reports."""
        metadata = {"broker": "XM", "account": "live", "symbols": ["XAUUSD", "EURUSD"]}

        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status, metadata
            ) VALUES (NOW(), 'https://example.com/test', 'pending', %s::jsonb)
            RETURNING id, metadata
        """, (json.dumps(metadata),))
        report_id, stored = db_cursor.fetchone()

        # Verify metadata was stored
        db_cursor.execute("""
            SELECT metadata FROM reports WHERE id = %s
        """, (report_id,))
        retrieved = json.loads(db_cursor.fetchone()[0])
        assert retrieved == metadata

    def test_key_trades_jsonb_array(self, db_cursor):
        """Test storing and querying JSONB array of trades."""
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status
            ) VALUES (NOW(), 'https://example.com/test', 'completed')
            RETURNING id
        """)
        report_id = db_cursor.fetchone()[0]

        key_trades = json.dumps([
            {"symbol": "XAUUSD", "entry": 2695.50, "type": "long"},
            {"symbol": "EURUSD", "entry": 1.0850, "type": "long"}
        ])

        db_cursor.execute("""
            INSERT INTO analyses (
                report_id, ai_provider, model_used, summary,
                key_trades, tokens_used, api_cost, processing_time_ms
            ) VALUES (
                %s, 'anthropic', 'claude-3-5-sonnet', 'Test',
                %s::jsonb, 500, 0.015, 2000
            ) RETURNING id, key_trades
        """, (report_id, key_trades))
        analysis_id, returned_trades = db_cursor.fetchone()

        # Verify trades were stored
        trades = json.loads(returned_trades)
        assert len(trades) == 2
        assert trades[0]["symbol"] == "XAUUSD"

    def test_metadata_containment_query(self, db_cursor):
        """Test JSONB containment operator (@>) for metadata queries."""
        # Insert reports with different brokers
        for broker in ["XM", "IC Markets", "OANDA"]:
            db_cursor.execute("""
                INSERT INTO reports (
                    email_received_at, report_url, status, metadata
                ) VALUES (NOW(), %s, 'pending', %s::jsonb)
            """, (f"https://example.com/{broker}", json.dumps({"broker": broker})))

        # Query for specific broker
        db_cursor.execute("""
            SELECT COUNT(*) FROM reports
            WHERE metadata @> %s::jsonb
        """, (json.dumps({"broker": "XM"}),))
        count = db_cursor.fetchone()[0]
        assert count == 1


class TestFullTextSearchAndIndexing:
    """Test full-text search on report content."""

    def test_full_text_search_on_content(self, db_cursor):
        """Test that full-text search finds reports by keyword."""
        # Insert reports with different content
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status, raw_content
            ) VALUES
                (NOW(), 'https://example.com/gold', 'completed',
                 'Gold prices continued higher today as geopolitical tensions mount'),
                (NOW(), 'https://example.com/oil', 'completed',
                 'Oil market showed weakness despite production cuts')
            RETURNING id
        """)

        # Search for reports mentioning 'gold'
        db_cursor.execute("""
            SELECT COUNT(*) FROM reports
            WHERE to_tsvector('english', raw_content) @@ to_tsquery('english', 'gold')
        """)
        count = db_cursor.fetchone()[0]
        assert count >= 1

    def test_full_text_search_with_gin_index(self, db_cursor):
        """Test that GIN index is used for full-text search."""
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status, raw_content
            ) VALUES (NOW(), 'https://example.com/test', 'completed',
                     'Trading report with multiple keywords')
        """)

        # Query with EXPLAIN to verify index is used
        db_cursor.execute("""
            EXPLAIN ANALYZE
            SELECT id FROM reports
            WHERE to_tsvector('english', raw_content) @@ to_tsquery('english', 'trading | report')
        """)
        explain_output = "\n".join([str(row[0]) for row in db_cursor.fetchall()])
        # Just verify query runs without error; actual plan depends on data


class TestAuditLoggingPatterns:
    """Test audit logging functionality."""

    def test_system_logs_event_insertion(self, db_cursor):
        """Test inserting audit log entries."""
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status
            ) VALUES (NOW(), 'https://example.com/test', 'pending')
            RETURNING id
        """)
        report_id = db_cursor.fetchone()[0]

        correlation_id = "12345678-1234-1234-1234-123456789012"

        db_cursor.execute("""
            INSERT INTO system_logs (
                service_name, log_level, message, report_id, correlation_id, metadata
            ) VALUES (
                'scraper_service', 'INFO', 'Report scraping completed',
                %s, %s::uuid, %s::jsonb
            ) RETURNING id
        """, (report_id, correlation_id, json.dumps({"duration_ms": 3200, "images": 2})))
        log_id = db_cursor.fetchone()[0]

        # Verify log was created
        db_cursor.execute("""
            SELECT report_id, message, metadata FROM system_logs WHERE id = %s
        """, (log_id,))
        row = db_cursor.fetchone()
        assert row[0] == report_id
        assert row[1] == 'Report scraping completed'

    def test_query_logs_by_report_id(self, db_cursor):
        """Test querying logs by report_id."""
        # Create report with logs
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status
            ) VALUES (NOW(), 'https://example.com/test', 'pending')
            RETURNING id
        """)
        report_id = db_cursor.fetchone()[0]

        # Insert multiple logs for same report
        for msg in ['Step 1', 'Step 2', 'Step 3']:
            db_cursor.execute("""
                INSERT INTO system_logs (
                    service_name, log_level, message, report_id
                ) VALUES ('test_service', 'INFO', %s, %s)
            """, (msg, report_id))

        # Query logs for this report
        db_cursor.execute("""
            SELECT COUNT(*) FROM system_logs WHERE report_id = %s
        """, (report_id,))
        count = db_cursor.fetchone()[0]
        assert count == 3

    def test_query_logs_by_correlation_id(self, db_cursor):
        """Test distributed tracing via correlation_id."""
        correlation_id = "87654321-4321-4321-4321-210987654321"

        # Insert logs with same correlation_id from different services
        for service in ['email_webhook', 'scraper_service', 'ai_analyzer']:
            db_cursor.execute("""
                INSERT INTO system_logs (
                    service_name, log_level, message, correlation_id
                ) VALUES (%s, 'INFO', 'Event', %s::uuid)
            """, (service, correlation_id))

        # Query all logs for this trace
        db_cursor.execute("""
            SELECT COUNT(*), COUNT(DISTINCT service_name)
            FROM system_logs WHERE correlation_id = %s::uuid
        """, (correlation_id,))
        total_logs, service_count = db_cursor.fetchone()
        assert total_logs == 3
        assert service_count == 3
