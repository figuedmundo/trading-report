#!/bin/bash
# Database restore script using pg_restore
# Restores a backup created by backup.sh
# Designed for disaster recovery

set -e  # Exit on any error

# Configuration
DB_NAME="${POSTGRES_DB:-trading_reports}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_FILE="${1:-}"

# Functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    log "ERROR: $1"
    exit 1
}

# Verify arguments
if [ -z "$BACKUP_FILE" ]; then
    error "Usage: $0 <backup_file>"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
fi

# Verify environment
if [ -z "$POSTGRES_PASSWORD" ]; then
    error "POSTGRES_PASSWORD environment variable not set"
fi

log "WARNING: This will RESTORE the database from backup"
log "Database: $DB_NAME"
log "Host: $DB_HOST"
log "Backup file: $BACKUP_FILE"
log "All existing data in $DB_NAME will be REPLACED"
echo ""
read -p "Are you sure? Type 'yes' to continue: " confirm

if [ "$confirm" != "yes" ]; then
    log "Restore cancelled"
    exit 0
fi

# Export password for psql
export PGPASSWORD="$POSTGRES_PASSWORD"

log "Starting database restore..."

# Drop existing database (if it exists)
log "Dropping existing database (if exists)..."
psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d postgres \
    -c "DROP DATABASE IF EXISTS $DB_NAME;" || true

# Create fresh database
log "Creating new database..."
psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d postgres \
    -c "CREATE DATABASE $DB_NAME;" \
    || error "Failed to create database"

# Restore from backup
log "Restoring from backup..."
if file "$BACKUP_FILE" | grep -q gzip; then
    # File is gzipped
    gunzip -c "$BACKUP_FILE" | psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        || error "Restore failed"
else
    # File is plain SQL
    psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -f "$BACKUP_FILE" \
        || error "Restore failed"
fi

log "Restore completed successfully"

# Verify restore
log "Verifying restored database..."
psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -c "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema='public';" \
    || error "Verification failed"

log "Database restore completed successfully"
