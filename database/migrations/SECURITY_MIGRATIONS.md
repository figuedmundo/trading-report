# Security Tables Migrations (009-011)

## Overview

Three new migrations have been created to support webhook endpoint security and rate limiting:

- **009_create_ip_allowlist_table.sql** - Dynamic IP allowlist management
- **010_create_security_events_table.sql** - Security event audit logging
- **011_create_ip_bans_table.sql** - Persistent IP ban storage

## Running Migrations

### Using Docker Compose

```bash
# Start PostgreSQL service
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
docker-compose logs -f postgres

# Run migrations
docker-compose exec postgres psql -U postgres -d trading_reports -f /docker-entrypoint-initdb.d/../migrations/009_create_ip_allowlist_table.sql
docker-compose exec postgres psql -U postgres -d trading_reports -f /docker-entrypoint-initdb.d/../migrations/010_create_security_events_table.sql
docker-compose exec postgres psql -U postgres -d trading_reports -f /docker-entrypoint-initdb.d/../migrations/011_create_ip_bans_table.sql
```

### Using Migration Script

```bash
# Set environment variables
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=trading_reports

# Run all migrations
python3 database/scripts/run_migrations.py
```

### Manual Execution

```bash
# Connect to database
psql -U postgres -d trading_reports

# Run migrations one by one
\i database/migrations/009_create_ip_allowlist_table.sql
\i database/migrations/010_create_security_events_table.sql
\i database/migrations/011_create_ip_bans_table.sql
```

## Verification

After running migrations, verify the tables exist:

```sql
-- List all tables
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Expected new tables:
-- - ip_allowlist
-- - security_events
-- - ip_bans

-- Verify indexes
SELECT tablename, indexname FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN ('ip_allowlist', 'security_events', 'ip_bans')
ORDER BY tablename, indexname;

-- Verify triggers
SELECT tgname, tgrelid::regclass, tgtype
FROM pg_trigger
WHERE tgrelid::regclass::text IN ('ip_allowlist')
ORDER BY tgname;
```

## Testing

Run the database migration tests:

```bash
# From project root
cd services/email-webhook
pytest tests/test_db_migrations.py -v

# Or run specific test
pytest tests/test_db_migrations.py::test_ip_allowlist_crud_operations -v
pytest tests/test_db_migrations.py::test_security_events_insert_and_query -v
pytest tests/test_db_migrations.py::test_ip_allowlist_updated_at_trigger -v
```

## Migration Details

### 009_create_ip_allowlist_table.sql

Creates the `ip_allowlist` table for dynamic IP whitelist management.

**Table Structure:**
- `id` (UUID) - Primary key
- `ip_address` (VARCHAR 45) - IP address or CIDR range, unique
- `description` (TEXT) - Human-readable description
- `enabled` (BOOLEAN) - Soft delete flag
- `created_at` (TIMESTAMPTZ) - Creation timestamp
- `updated_at` (TIMESTAMPTZ) - Last update timestamp

**Features:**
- Partial index on `enabled=true` for fast queries
- Automatic `updated_at` trigger
- CIDR range support (e.g., 192.168.1.0/24)
- Soft delete pattern

**Usage Examples:**
```sql
-- Add new IP
INSERT INTO ip_allowlist (ip_address, description)
VALUES ('149.72.0.0/16', 'Mailgun IP range');

-- Query enabled IPs
SELECT ip_address FROM ip_allowlist WHERE enabled = true;

-- Soft delete IP
UPDATE ip_allowlist SET enabled = false WHERE ip_address = '1.2.3.4';

-- Re-enable IP
UPDATE ip_allowlist SET enabled = true WHERE ip_address = '1.2.3.4';
```

### 010_create_security_events_table.sql

Creates the `security_events` table for comprehensive security audit logging.

**Table Structure:**
- `id` (UUID) - Primary key
- `event_type` (VARCHAR 50) - Event type identifier
- `ip_address` (VARCHAR 45) - Source IP address
- `endpoint` (VARCHAR 255) - Request endpoint
- `request_headers` (JSONB) - Filtered request headers
- `metadata` (JSONB) - Event-specific metadata
- `created_at` (TIMESTAMPTZ) - Event timestamp

**Event Types:**
- `signature_validation_failed` - Invalid or missing signature
- `ip_not_whitelisted` - IP not in allowlist
- `rate_limit_exceeded` - Rate limit violation
- `ip_banned` - IP banned for repeated violations
- `ip_unbanned` - IP manually unbanned
- `suspicious_pattern` - Detected attack pattern
- `connection_throttled` - Concurrent connection limit reached

**Indexes:**
- `idx_security_events_ip` - Query events by IP
- `idx_security_events_type` - Filter by event type
- `idx_security_events_created` - Time-range queries (DESC)
- `idx_security_events_type_created` - Composite index for filtered time queries

**Usage Examples:**
```sql
-- Log security event
INSERT INTO security_events (event_type, ip_address, endpoint, metadata)
VALUES (
    'rate_limit_exceeded',
    '192.168.1.100',
    '/webhook/email',
    '{"rate_limit_remaining": 0, "limit_type": "per_ip_minute"}'::jsonb
);

-- Query recent failures
SELECT * FROM security_events
WHERE event_type = 'signature_validation_failed'
AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

-- Count events per IP
SELECT ip_address, event_type, COUNT(*) as count
FROM security_events
WHERE created_at > NOW() - INTERVAL '10 minutes'
GROUP BY ip_address, event_type
HAVING COUNT(*) > 50;

-- Find suspicious patterns
SELECT ip_address, COUNT(*) as failure_count
FROM security_events
WHERE created_at > NOW() - INTERVAL '10 minutes'
AND event_type IN ('signature_validation_failed', 'rate_limit_exceeded')
GROUP BY ip_address
HAVING COUNT(*) > 50;
```

### 011_create_ip_bans_table.sql

Creates the `ip_bans` table for persistent IP ban storage across service restarts.

**Table Structure:**
- `id` (UUID) - Primary key
- `ip_address` (VARCHAR 45) - Banned IP address
- `banned_until` (TIMESTAMPTZ) - Ban expiry timestamp
- `reason` (TEXT) - Ban reason
- `attempt_count` (INTEGER) - Failed attempts that triggered ban
- `created_at` (TIMESTAMPTZ) - Ban creation timestamp

**Indexes:**
- `idx_ip_bans_ip` - Fast ban lookups
- `idx_ip_bans_banned_until` - Cleanup queries and expiry checks

**Usage Examples:**
```sql
-- Ban an IP
INSERT INTO ip_bans (ip_address, banned_until, reason, attempt_count)
VALUES (
    '10.0.0.50',
    NOW() + INTERVAL '1 hour',
    'Exceeded rate limit threshold',
    15
);

-- Check if IP is banned
SELECT EXISTS(
    SELECT 1 FROM ip_bans
    WHERE ip_address = '10.0.0.50'
    AND banned_until > NOW()
) as is_banned;

-- Cleanup expired bans
DELETE FROM ip_bans WHERE banned_until <= NOW();

-- List active bans
SELECT ip_address, banned_until, reason, attempt_count
FROM ip_bans
WHERE banned_until > NOW()
ORDER BY created_at DESC;

-- Manual unban
DELETE FROM ip_bans WHERE ip_address = '10.0.0.50';
```

## Rollback

If you need to rollback these migrations:

```sql
BEGIN;

-- Drop tables in reverse order (to handle dependencies)
DROP TABLE IF EXISTS ip_bans CASCADE;
DROP TABLE IF EXISTS security_events CASCADE;
DROP TABLE IF EXISTS ip_allowlist CASCADE;

-- Drop trigger function
DROP FUNCTION IF EXISTS update_ip_allowlist_updated_at() CASCADE;

COMMIT;
```

**Warning:** Rollback will delete all data in these tables. Consider exporting data first:

```bash
# Export data before rollback
pg_dump -U postgres -d trading_reports -t ip_allowlist -t security_events -t ip_bans > security_tables_backup.sql
```

## Integration with Services

These tables are used by:
- **email-webhook service** - IP whitelisting, rate limiting, security logging
- **notification-service** - Security alerts via Telegram
- **database maintenance scripts** - Periodic cleanup of old security events

## Maintenance

### Cleanup Old Security Events

```sql
-- Delete events older than 90 days
DELETE FROM security_events
WHERE created_at < NOW() - INTERVAL '90 days';

-- Or archive instead of delete
CREATE TABLE IF NOT EXISTS security_events_archive AS
SELECT * FROM security_events WHERE 1=0;

INSERT INTO security_events_archive
SELECT * FROM security_events
WHERE created_at < NOW() - INTERVAL '90 days';

DELETE FROM security_events
WHERE created_at < NOW() - INTERVAL '90 days';
```

### Monitor Table Sizes

```sql
-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('ip_allowlist', 'security_events', 'ip_bans')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Vacuum and Analyze

```bash
# After large deletions or updates
psql -U postgres -d trading_reports -c "VACUUM ANALYZE ip_allowlist;"
psql -U postgres -d trading_reports -c "VACUUM ANALYZE security_events;"
psql -U postgres -d trading_reports -c "VACUUM ANALYZE ip_bans;"
```

## References

- **Spec**: `agent-os/specs/2025-11-27-webhook-security-rate-limiting/spec.md`
- **Requirements**: `agent-os/specs/2025-11-27-webhook-security-rate-limiting/planning/requirements.md`
- **Migration Standards**: `agent-os/standards/backend/migrations.md`
- **Database Patterns**: `database/migrations/006_create_analyses_table.sql`
