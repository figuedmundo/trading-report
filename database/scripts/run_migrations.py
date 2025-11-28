#!/usr/bin/env python3
"""
Database migration runner script.

Applies all SQL migration files from database/migrations/ in order.
Migrations are idempotent and can be safely re-run.

Environment variables required:
- POSTGRES_USER (default: postgres)
- POSTGRES_PASSWORD (required)
- POSTGRES_HOST (default: localhost)
- POSTGRES_PORT (default: 5432)
- POSTGRES_DB (default: trading_reports)
"""

import psycopg2
import os
import sys
from pathlib import Path
from psycopg2 import OperationalError


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


def connect_to_database():
    """Connect to PostgreSQL database."""
    log("Connecting to PostgreSQL database...")
    try:
        conn = psycopg2.connect(
            dbname=get_env("POSTGRES_DB", "trading_reports"),
            user=get_env("POSTGRES_USER", "postgres"),
            password=get_env("POSTGRES_PASSWORD"),
            host=get_env("POSTGRES_HOST", "localhost"),
            port=get_env("POSTGRES_PORT", "5432"),
            connect_timeout=10
        )
        log("Connected to database successfully")
        return conn
    except OperationalError as e:
        log(f"Failed to connect: {e}", "ERROR")
        raise


def get_migration_files(migrations_dir: Path) -> list[Path]:
    """Get all migration SQL files sorted by filename."""
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

    migration_files = sorted(migrations_dir.glob("*.sql"))
    log(f"Found {len(migration_files)} migration files")
    return migration_files


def apply_migration(cursor, migration_file: Path) -> bool:
    """Apply a single migration file."""
    log(f"Applying migration: {migration_file.name}")

    try:
        with open(migration_file, "r") as f:
            migration_sql = f.read()

        cursor.execute(migration_sql)
        log(f"Successfully applied: {migration_file.name}", "SUCCESS")
        return True

    except Exception as e:
        log(f"Failed to apply {migration_file.name}: {e}", "ERROR")
        raise


def run_migrations():
    """Main migration runner function."""
    log("Starting database migrations...")

    # Get migrations directory
    script_dir = Path(__file__).parent
    migrations_dir = script_dir.parent / "migrations"

    conn = None
    try:
        # Connect to database
        conn = connect_to_database()
        cursor = conn.cursor()

        # Get migration files
        migration_files = get_migration_files(migrations_dir)

        if not migration_files:
            log("No migration files found")
            return 0

        # Apply each migration
        applied_count = 0
        for migration_file in migration_files:
            try:
                apply_migration(cursor, migration_file)
                conn.commit()
                applied_count += 1
            except Exception as e:
                conn.rollback()
                log(f"Migration failed, rolled back: {e}", "ERROR")
                raise

        log(f"Successfully applied {applied_count} migrations!")
        return 0

    except Exception as e:
        log(f"Migration process failed: {e}", "ERROR")
        if conn:
            conn.rollback()
        return 1

    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    sys.exit(run_migrations())
