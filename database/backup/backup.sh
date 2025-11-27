#!/bin/bash
# Database backup script using pg_dump
# Creates a compressed backup of the trading_reports database
# Designed for daily automated backups

set -e  # Exit on any error

# Configuration
DB_NAME="${POSTGRES_DB:-trading_reports}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

# Functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    log "ERROR: $1"
    exit 1
}

# Verify environment
if [ -z "$POSTGRES_PASSWORD" ]; then
    error "POSTGRES_PASSWORD environment variable not set"
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR" || error "Failed to create backup directory: $BACKUP_DIR"

log "Starting database backup..."
log "Database: $DB_NAME"
log "Host: $DB_HOST"
log "Backup file: $BACKUP_FILE"

# Export password for pg_dump
export PGPASSWORD="$POSTGRES_PASSWORD"

# Perform backup
if pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --verbose \
    --format=plain | gzip > "$BACKUP_FILE"; then
    log "Backup completed successfully"
    log "Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
else
    error "Backup failed"
fi

# Verify backup integrity
log "Verifying backup integrity..."
if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
    log "Backup verification passed"
else
    error "Backup verification failed - file may be corrupted"
fi

# Clean up old backups
log "Cleaning up backups older than $BACKUP_RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime "+$BACKUP_RETENTION_DAYS" -delete
log "Old backups cleaned"

# List recent backups
log "Recent backups:"
ls -lh "$BACKUP_DIR"/${DB_NAME}_*.sql.gz 2>/dev/null | tail -5

log "Backup script completed successfully"
