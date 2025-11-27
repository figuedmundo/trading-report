"""Pytest configuration and fixtures for database tests."""

import os
import psycopg2
from psycopg2 import sql
import pytest


@pytest.fixture(scope="session")
def db_connection():
    """
    Create a database connection for the test session.
    Uses environment variables or sensible defaults.
    """
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "trading_reports"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )
    yield conn
    conn.close()


@pytest.fixture
def db_cursor(db_connection):
    """
    Create a database cursor with automatic rollback after each test.
    This isolates tests and prevents data pollution.
    """
    cursor = db_connection.cursor()
    yield cursor
    cursor.close()
    # Rollback any changes from the test
    db_connection.rollback()


@pytest.fixture
def setup_teardown_table(db_connection):
    """
    Helper to create test tables and clean them up.
    Used for testing CASCADE DELETE behavior.
    """
    def _setup(table_name):
        cursor = db_connection.cursor()
        # Table is assumed to exist from schema
        cursor.execute(f"TRUNCATE TABLE {sql.Identifier(table_name).as_string(cursor)} CASCADE")
        db_connection.commit()
        cursor.close()

    yield _setup

    # Cleanup: truncate all tables
    cursor = db_connection.cursor()
    tables = ["notifications", "analyses", "report_images", "system_logs", "reports"]
    for table in tables:
        try:
            cursor.execute(f"TRUNCATE TABLE {sql.Identifier(table).as_string(cursor)} CASCADE")
        except Exception:
            pass
    db_connection.commit()
    cursor.close()
