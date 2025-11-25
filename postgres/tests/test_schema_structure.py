"""
Schema structure validation tests for trading reports database.

These focused tests verify that the database schema has been applied correctly
and that all critical elements are present and functioning.
"""

import pytest


class TestTablesExist:
    """Test that all required tables exist with correct structure."""

    def test_all_tables_exist(self, db_cursor):
        """Verify all 5 required tables exist in public schema."""
        db_cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = {row[0] for row in db_cursor.fetchall()}

        expected_tables = {
            "analyses",
            "notifications",
            "report_images",
            "reports",
            "system_logs"
        }

        assert expected_tables == tables, f"Missing or extra tables. Expected {expected_tables}, got {tables}"

    def test_reports_table_structure(self, db_cursor):
        """Verify reports table has all required columns."""
        db_cursor.execute("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name = 'reports'
            ORDER BY column_name
        """)
        columns = {row[0]: row[1] for row in db_cursor.fetchall()}

        required_columns = {
            "id": "uuid",
            "email_from": "text",
            "email_message_id": "text",
            "email_received_at": "timestamp with time zone",
            "email_subject": "text",
            "report_url": "text",
            "report_title": "text",
            "raw_content": "text",
            "status": "report_status",
            "error_message": "text",
            "retry_count": "integer",
            "last_retry_at": "timestamp with time zone",
            "metadata": "jsonb",
            "created_at": "timestamp with time zone",
            "updated_at": "timestamp with time zone",
            "processed_at": "timestamp with time zone"
        }

        for col, dtype in required_columns.items():
            assert col in columns, f"Column '{col}' missing from reports table"
            assert columns[col] == dtype, f"Column '{col}' has type {columns[col]}, expected {dtype}"

    def test_analyses_table_structure(self, db_cursor):
        """Verify analyses table has all required columns."""
        db_cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'analyses'
        """)
        columns = {row[0] for row in db_cursor.fetchall()}

        required_columns = {
            "id", "report_id", "ai_provider", "model_used", "prompt_template",
            "summary", "key_trades", "market_analysis", "recommendations",
            "sentiment", "confidence_score", "win_rate", "profit_loss",
            "total_trades", "tokens_used", "api_cost", "processing_time_ms",
            "metadata", "created_at"
        }

        assert required_columns.issubset(columns), \
            f"Analyses missing columns: {required_columns - columns}"

    def test_notifications_table_structure(self, db_cursor):
        """Verify notifications table has all required columns."""
        db_cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'notifications'
        """)
        columns = {row[0] for row in db_cursor.fetchall()}

        required_columns = {
            "id", "analysis_id", "channel", "recipient", "status",
            "sent_at", "error_message", "retry_count", "max_retries",
            "message_id", "message_content", "metadata",
            "created_at", "updated_at"
        }

        assert required_columns.issubset(columns), \
            f"Notifications missing columns: {required_columns - columns}"


class TestEnumTypesExist:
    """Test that all custom ENUM types are defined."""

    def test_enum_types_exist(self, db_cursor):
        """Verify all 5 ENUM types are created."""
        db_cursor.execute("""
            SELECT typname FROM pg_type
            WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            AND typtype = 'e'
            ORDER BY typname
        """)
        enums = {row[0] for row in db_cursor.fetchall()}

        expected_enums = {
            "report_status",
            "notification_channel",
            "notification_status",
            "ai_provider",
            "sentiment"
        }

        assert expected_enums == enums, f"Expected {expected_enums}, got {enums}"

    def test_report_status_enum_values(self, db_cursor):
        """Verify report_status ENUM has correct values."""
        db_cursor.execute("""
            SELECT enum_range(NULL::report_status)
        """)
        result = db_cursor.fetchone()[0]
        # enum_range returns string like "pending,processing,completed,failed"
        values = set(result.split(","))
        expected = {"pending", "processing", "completed", "failed"}
        assert values == expected, f"Expected {expected}, got {values}"


class TestViewsExist:
    """Test that all required views are created."""

    def test_all_views_exist(self, db_cursor):
        """Verify all 3 required views exist."""
        db_cursor.execute("""
            SELECT viewname FROM pg_views
            WHERE schemaname = 'public'
            ORDER BY viewname
        """)
        views = {row[0] for row in db_cursor.fetchall()}

        expected_views = {
            "vw_reports_with_analysis",
            "vw_notification_stats",
            "vw_daily_metrics"
        }

        assert expected_views.issubset(views), \
            f"Missing views: {expected_views - views}"

    def test_vw_reports_with_analysis_columns(self, db_cursor):
        """Verify vw_reports_with_analysis has expected columns."""
        db_cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'vw_reports_with_analysis'
        """)
        columns = {row[0] for row in db_cursor.fetchall()}

        expected_cols = {
            "id", "email_received_at", "email_subject", "report_url",
            "status", "created_at", "processed_at", "analysis_id",
            "ai_provider", "summary", "sentiment", "confidence_score",
            "key_trades", "image_count", "notification_count", "notifications_sent"
        }

        assert expected_cols.issubset(columns), \
            f"View missing columns: {expected_cols - columns}"


class TestTriggersAndFunctions:
    """Test that triggers and functions are created and functional."""

    def test_triggers_exist(self, db_cursor):
        """Verify all required triggers are created."""
        db_cursor.execute("""
            SELECT trigger_name, event_object_table FROM information_schema.triggers
            WHERE trigger_schema = 'public'
            ORDER BY trigger_name
        """)
        triggers = {(row[0], row[1]) for row in db_cursor.fetchall()}

        expected_triggers = {
            ("update_reports_updated_at", "reports"),
            ("set_report_processed_at", "reports"),
            ("update_notifications_updated_at", "notifications")
        }

        assert expected_triggers.issubset(triggers), \
            f"Missing triggers: {expected_triggers - triggers}"

    def test_update_updated_at_trigger(self, db_cursor):
        """Test that update_updated_at trigger works on reports table."""
        # Insert a test report
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status
            ) VALUES (
                NOW(), 'https://example.com/test', 'pending'
            ) RETURNING id, updated_at as initial_updated_at
        """)
        report_id, initial_updated = db_cursor.fetchone()

        # Sleep a moment to ensure time difference
        import time
        time.sleep(0.1)

        # Update the report
        db_cursor.execute("""
            UPDATE reports SET status = 'processing'
            WHERE id = %s
            RETURNING updated_at
        """)
        new_updated = db_cursor.fetchone()[0]

        # Verify updated_at was changed automatically
        assert new_updated > initial_updated, \
            "Trigger did not update 'updated_at' timestamp"

    def test_set_processed_at_trigger(self, db_cursor):
        """Test that set_processed_at trigger sets timestamp when status = completed."""
        # Insert test report with status 'pending'
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status
            ) VALUES (
                NOW(), 'https://example.com/test2', 'pending'
            ) RETURNING id, processed_at
        """)
        report_id, initial_processed = db_cursor.fetchone()

        # Verify processed_at is NULL initially
        assert initial_processed is None, "processed_at should be NULL for pending report"

        # Update status to completed
        db_cursor.execute("""
            UPDATE reports SET status = 'completed'
            WHERE id = %s
            RETURNING processed_at
        """)
        final_processed = db_cursor.fetchone()[0]

        # Verify processed_at was set automatically
        assert final_processed is not None, \
            "Trigger did not set 'processed_at' when status became 'completed'"


class TestIndexesExist:
    """Test that critical indexes are created."""

    def test_critical_indexes_exist(self, db_cursor):
        """Verify key indexes are created for performance."""
        db_cursor.execute("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY indexname
        """)
        indexes = {row[0] for row in db_cursor.fetchall()}

        critical_indexes = {
            "idx_reports_created_at",
            "idx_reports_status",
            "idx_analyses_report_id",
            "idx_images_report_id",
            "idx_notifications_status",
            "idx_logs_report_id"
        }

        assert critical_indexes.issubset(indexes), \
            f"Missing critical indexes: {critical_indexes - indexes}"

    def test_partial_index_on_status(self, db_cursor):
        """Verify partial index on reports.status where status != 'completed'."""
        db_cursor.execute("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_reports_status'
        """)
        index_def = db_cursor.fetchone()

        assert index_def is not None, "Partial index idx_reports_status not found"
        assert "WHERE" in index_def[0], "Index should be partial (have WHERE clause)"
        assert "status" in index_def[0].lower(), "Index should reference status column"

    def test_gin_index_on_full_text_search(self, db_cursor):
        """Verify GIN index exists on raw_content for full-text search."""
        db_cursor.execute("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_reports_content_search'
        """)
        index_def = db_cursor.fetchone()

        assert index_def is not None, "Full-text search index not found"
        assert "gin" in index_def[0].lower(), "Index should use GIN access method"


class TestConstraints:
    """Test that constraints are properly defined."""

    def test_unique_constraint_on_email_message_id(self, db_cursor):
        """Verify UNIQUE constraint on reports.email_message_id."""
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, email_message_id, status
            ) VALUES (
                NOW(), 'https://example.com/test', '<test@example.com>', 'pending'
            )
        """)

        # Try to insert duplicate email_message_id
        with pytest.raises(Exception):
            db_cursor.execute("""
                INSERT INTO reports (
                    email_received_at, report_url, email_message_id, status
                ) VALUES (
                    NOW(), 'https://example.com/test2', '<test@example.com>', 'pending'
                )
            """)

    def test_url_validation_constraint(self, db_cursor):
        """Verify URL validation constraint on report_url."""
        # Valid URL should work
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status
            ) VALUES (
                NOW(), 'https://example.com/valid', 'pending'
            )
        """)

        # Invalid URL should fail
        with pytest.raises(Exception):
            db_cursor.execute("""
                INSERT INTO reports (
                    email_received_at, report_url, status
                ) VALUES (
                    NOW(), 'not-a-valid-url', 'pending'
                )
            """)

    def test_retry_count_non_negative_constraint(self, db_cursor):
        """Verify retry_count must be >= 0."""
        # Valid retry_count
        db_cursor.execute("""
            INSERT INTO reports (
                email_received_at, report_url, status, retry_count
            ) VALUES (
                NOW(), 'https://example.com/test', 'pending', 0
            )
        """)

        # Negative retry_count should fail
        with pytest.raises(Exception):
            db_cursor.execute("""
                INSERT INTO reports (
                    email_received_at, report_url, status, retry_count
                ) VALUES (
                    NOW(), 'https://example.com/test2', 'pending', -1
                )
            """)
