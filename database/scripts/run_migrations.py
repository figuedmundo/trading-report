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
    """Connect to PostgreSQL database with retry logic."""
    log("Connecting to PostgreSQL database...")
    import time

    max_retries = 60
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            # During Docker initialization, try Unix socket first (local), then TCP
            # The Unix socket is available as soon as postgres starts
            try:
                # Try Unix socket connection (fastest for local)
                conn = psycopg2.connect(
                    dbname=get_env("POSTGRES_DB", "trading_reports"),
                    user=get_env("POSTGRES_USER", "postgres"),
                    password=get_env("POSTGRES_PASSWORD"),
                    connect_timeout=2
                )
                log("Connected to database successfully (via Unix socket)")
                return conn
            except OperationalError:
                # Unix socket failed, try TCP
                host = os.getenv("POSTGRES_HOST", "localhost")
                conn = psycopg2.connect(
                    dbname=get_env("POSTGRES_DB", "trading_reports"),
                    user=get_env("POSTGRES_USER", "postgres"),
                    password=get_env("POSTGRES_PASSWORD"),
                    host=host,
                    port=get_env("POSTGRES_PORT", "5432"),
                    connect_timeout=2
                )
                log(f"Connected to database successfully (via {host}:{get_env('POSTGRES_PORT', '5432')})")
                return conn

        except OperationalError as e:
            if attempt < max_retries - 1:
                log(f"Connection attempt {attempt + 1}/{max_retries} failed, retrying in {retry_delay}s...", "WARNING")
                time.sleep(retry_delay)
            else:
                log(f"Failed to connect after {max_retries} attempts: {e}", "ERROR")
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

def create_application_users(cursor):
    """Create n8n and trading_user if they don't exist."""
    db_name = get_env("POSTGRES_DB", "trading_reports")

    # Create n8n user
    n8n_user = get_env("N8N_DB_USER", "n8n_user")
    n8n_password = get_env("N8N_DB_PASSWORD")

    try:
        log(f"Checking if user {n8n_user} exists...")
        cursor.execute(f"SELECT 1 FROM pg_roles WHERE rolname='{n8n_user}'")
        if not cursor.fetchone():
            log(f"Creating user {n8n_user}...")
            cursor.execute(f"CREATE USER {n8n_user} WITH PASSWORD '{n8n_password}'")
            log(f"User {n8n_user} created successfully")
        else:
            log(f"User {n8n_user} already exists")

        log(f"Granting privileges on database {db_name} to {n8n_user}...")
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {n8n_user}")
        log("Privileges granted successfully")

    except Exception as e:
        log(f"Failed to create n8n user: {e}", "ERROR")
        raise

    # Create trading_user
    trading_user = "trading_user"
    trading_password = get_env("TRADING_USER_PASSWORD")

    try:
        log(f"Checking if user {trading_user} exists...")
        cursor.execute(f"SELECT 1 FROM pg_roles WHERE rolname='{trading_user}'")
        if not cursor.fetchone():
            log(f"Creating user {trading_user}...")
            cursor.execute(f"CREATE USER {trading_user} WITH PASSWORD '{trading_password}'")
            log(f"User {trading_user} created successfully")
        else:
            log(f"User {trading_user} already exists")

        log(f"Granting privileges on database {db_name} to {trading_user}...")
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {trading_user}")
        log("Privileges granted successfully")

    except Exception as e:
        log(f"Failed to create trading_user: {e}", "ERROR")
        raise


def grant_table_permissions(cursor):
    """Grant table permissions to application users after migrations."""
    db_name = get_env("POSTGRES_DB", "trading_reports")

    try:
        log("Granting table permissions to trading_user...")
        # Essential: Grant CREATE schema permissions
        cursor.execute(f"GRANT USAGE, CREATE ON SCHEMA public TO trading_user")
        
        cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO trading_user")
        cursor.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO trading_user")
        cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trading_user")
        log("Permissions granted to trading_user successfully")

        log("Granting table permissions to n8n_user...")
        # Essential: Grant CREATE schema permissions for n8n to create migrations table
        cursor.execute(f"GRANT ALL PRIVILEGES ON SCHEMA public TO n8n_user")
        cursor.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO n8n_user")
        cursor.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO n8n_user")
        cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO n8n_user")
        log("Permissions granted to n8n_user successfully")

        # Disable RLS on notifications_delivery_log if it exists
        try:
            cursor.execute("ALTER TABLE notifications_delivery_log DISABLE ROW LEVEL SECURITY")
            log("Disabled RLS on notifications_delivery_log")
        except Exception as e:
            log(f"Could not disable RLS (table might not exist yet): {e}", "WARNING")

    except Exception as e:
        log(f"Failed to grant table permissions: {e}", "ERROR")
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

        # Create application users (n8n and trading_user)
        create_application_users(cursor)
        conn.commit()

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

        # Grant table permissions to application users
        grant_table_permissions(cursor)
        conn.commit()

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