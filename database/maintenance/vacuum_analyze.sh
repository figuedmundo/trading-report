#!/bin/bash
# Database maintenance script: VACUUM and ANALYZE
# This script performs maintenance operations to keep the database performant
# Should be run daily (typically during low-traffic periods)

set -e  # Exit on any error

# Configuration
DB_NAME="${POSTGRES_DB:-trading_reports}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
LOG_FILE="${LOG_FILE:-./db_maintenance.log}"

# Functions
log() {
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

error() {
    log "ERROR: $1"
    exit 1
}

# Verify environment
if [ -z "$POSTGRES_PASSWORD" ]; then
    error "POSTGRES_PASSWORD environment variable not set"
fi

log "Starting database maintenance..."

# Export password for psql
export PGPASSWORD="$POSTGRES_PASSWORD"

# Run VACUUM ANALYZE
log "Running VACUUM ANALYZE on $DB_NAME..."
psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -c "VACUUM ANALYZE;" \
    || error "VACUUM ANALYZE failed"

log "Maintenance completed successfully"

# Optional: Get table sizes after maintenance
log "Database table sizes after maintenance:"
psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables WHERE schemaname='public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;" \
    | tee -a "$LOG_FILE"

log "Maintenance script completed"
