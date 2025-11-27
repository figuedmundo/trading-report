#!/usr/bin/env python3
"""
Database initialization script for trading_reports database.

This script:
1. Reads the production-ready schema from database_schema.sql
2. Creates the trading_reports database
3. Creates the trading_user role with appropriate permissions
4. Applies the schema to establish all tables, indexes, views, and triggers
5. Enables required extensions (uuid-ossp, pg_trgm)
6. Is idempotent (safe to re-run multiple times)

Environment variables required:
- POSTGRES_USER (default: postgres)
- POSTGRES_PASSWORD (required)
- POSTGRES_HOST (default: localhost)
- POSTGRES_PORT (default: 5432)
"""

import psycopg2
import os
import sys
from pathlib import Path
from psycopg2 import sql, OperationalError, ProgrammingError


def get_env(key: str, default: str = None) -> str:
    """Get environment variable or use default."""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable {key} is required")
    return value


def log(message: str, level: str = "INFO") -> None:
    """Log message with timestamp."""
    import datetime
    timestamp = datetime.datetime.now().isoformat()
    print(f"[{timestamp}] {level}: {message}")


def connect_as_superuser():
    """Connect to PostgreSQL as superuser."""
    log("Connecting to PostgreSQL as superuser...")
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "postgres"),
            user=get_env("POSTGRES_USER", "postgres"),
            password=get_env("POSTGRES_PASSWORD"),
            host=get_env("POSTGRES_HOST", "localhost"),
            port=get_env("POSTGRES_PORT", "5432"),
            connect_timeout=10
        )
        log("Connected to PostgreSQL as superuser")
        return conn
    except OperationalError as e:
        log(f"Failed to connect: {e}", "ERROR")
        raise


def create_database(cursor, db_name: str) -> bool:
    """Create database if it doesn't exist."""
    try:
        cursor.execute(f"CREATE DATABASE {sql.Identifier(db_name).as_string(cursor)}")
        log(f"Created database '{db_name}'")
        return True
    except ProgrammingError as e:
        if "already exists" in str(e):
            log(f"Database '{db_name}' already exists")
            return False
        raise


def create_trading_user(cursor, password: str) -> bool:
    """Create trading_user role if it doesn't exist."""
    try:
        cursor.execute(
            sql.SQL("CREATE USER {user} WITH PASSWORD %s").format(
                user=sql.Identifier("trading_user")
            ),
            (password,)
        )
        log("Created user 'trading_user'")
        return True
    except ProgrammingError as e:
        if "already exists" in str(e):
            log("User 'trading_user' already exists")
            return False
        raise


def apply_schema(cursor, schema_path: Path) -> None:
    """Read and apply schema SQL file."""
    log(f"Reading schema from {schema_path}")
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, "r") as f:
        schema_sql = f.read()

    log("Applying schema to database...")
    cursor.execute(schema_sql)
    log("Schema applied successfully")


def grant_permissions(cursor) -> None:
    """Grant appropriate permissions to trading_user."""
    log("Granting permissions to trading_user...")

    # Connect permissions
    cursor.execute(
        "GRANT CONNECT ON DATABASE trading_reports TO trading_user"
    )

    # Schema permissions
    cursor.execute(
        "GRANT USAGE ON SCHEMA public TO trading_user"
    )

    # Table permissions
    tables = [
        "reports",
        "report_images",
        "analyses",
        "notifications",
        "system_logs"
    ]

    for table in tables:
        cursor.execute(
            sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO trading_user").format(
                table=sql.Identifier(table)
            )
        )

    # Sequence permissions for UUID generation
    cursor.execute(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO trading_user"
    )

    # Function permissions for triggers
    cursor.execute(
        "GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO trading_user"
    )

    log("Permissions granted successfully")


def verify_extensions(cursor) -> None:
    """Verify required extensions are enabled."""
    log("Verifying extensions...")

    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp')"
    )
    if not cursor.fetchone()[0]:
        raise RuntimeError("uuid-ossp extension not enabled")

    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')"
    )
    if not cursor.fetchone()[0]:
        raise RuntimeError("pg_trgm extension not enabled")

    log("Extensions verified")


def verify_schema(cursor) -> None:
    """Verify all expected tables exist."""
    log("Verifying schema...")

    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        "analyses",
        "notifications",
        "report_images",
        "reports",
        "system_logs"
    }

    missing = expected_tables - tables
    if missing:
        raise RuntimeError(f"Missing tables: {missing}")

    log(f"All expected tables exist: {sorted(tables)}")

    # Verify views
    cursor.execute("""
        SELECT viewname FROM pg_views
        WHERE schemaname = 'public'
        ORDER BY viewname
    """)
    views = {row[0] for row in cursor.fetchall()}

    expected_views = {
        "vw_reports_with_analysis",
        "vw_notification_stats",
        "vw_daily_metrics"
    }

    missing_views = expected_views - views
    if missing_views:
        raise RuntimeError(f"Missing views: {missing_views}")

    log(f"All expected views exist: {sorted(views)}")


def init_database():
    """Main initialization function."""
    log("Starting database initialization...")

    # Get configuration
    postgres_password = get_env("POSTGRES_PASSWORD")
    trading_user_password = os.getenv(
        "TRADING_USER_PASSWORD",
        postgres_password  # Use same password if not specified
    )
    schema_path = (
        Path(__file__).parent.parent /
        "agent-os/specs/2025-11-25-postgresql-schema-data-persistence/planning/database_schema.sql"
    )

    conn = None
    try:
        # Step 1: Connect as superuser
        conn = connect_as_superuser()
        cursor = conn.cursor()

        # Step 2: Create database
        db_created = create_database(cursor, "trading_reports")
        conn.commit()

        # Step 3: Close and reconnect to new database
        cursor.close()
        conn.close()

        log("Reconnecting to trading_reports database...")
        conn = psycopg2.connect(
            dbname="trading_reports",
            user=get_env("POSTGRES_USER", "postgres"),
            password=postgres_password,
            host=get_env("POSTGRES_HOST", "localhost"),
            port=get_env("POSTGRES_PORT", "5432"),
            connect_timeout=10
        )
        cursor = conn.cursor()

        # Step 4: Apply schema
        apply_schema(cursor, schema_path)
        conn.commit()

        # Step 5: Create user (if not exists)
        try:
            create_trading_user(cursor, trading_user_password)
            conn.commit()
        except ProgrammingError:
            conn.rollback()

        # Step 6: Grant permissions
        grant_permissions(cursor)
        conn.commit()

        # Step 7: Verify
        verify_extensions(cursor)
        verify_schema(cursor)

        log("Database initialization completed successfully!")
        log("You can now connect as trading_user:")
        log(f"  psql -U trading_user -d trading_reports")
        log(f"  Or via connection string:")
        log(f"  postgresql://trading_user:PASSWORD@{get_env('POSTGRES_HOST', 'localhost')}:5432/trading_reports")

        return 0

    except Exception as e:
        log(f"Initialization failed: {e}", "ERROR")
        if conn:
            conn.rollback()
        return 1

    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    sys.exit(init_database())
