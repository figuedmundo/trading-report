# Database Migrations

This directory contains all schema change migrations for the trading_reports database.

## Overview

Migrations are SQL files that make incremental changes to the database schema. They enable:
- Version control of database structure
- Rollback capability if issues arise
- Clear change history for debugging
- Coordination across team members

## Migration Naming Convention

All migration files follow this naming pattern:

```
YYYY_MM_DD_HH_MM_description.sql
```

**Examples**:
```
2025_11_25_09_00_create_trading_tables.sql
2025_11_25_14_30_add_index_on_status.sql
2025_11_26_10_15_add_metadata_column.sql
```

**Components**:
- `YYYY` - Year (4 digits)
- `MM` - Month (2 digits)
- `DD` - Day (2 digits)
- `HH` - Hour in 24-hour format (2 digits)
- `MM` - Minute (2 digits)
- `description` - Brief description using underscores (not spaces)

## Migration File Structure

Every migration must follow this structure for safety:

```sql
-- Migration: Add new column to reports table
-- Description: Add external_id column for third-party integrations
-- Date: 2025-11-26
-- Author: development-team

BEGIN;

-- Step 1: Add column
ALTER TABLE reports ADD COLUMN external_id VARCHAR(255);

-- Step 2: Add index
CREATE INDEX idx_reports_external_id ON reports(external_id) WHERE external_id IS NOT NULL;

-- Step 3: Update permissions
GRANT SELECT ON reports TO analytics_user;

-- Verify migration success
SELECT COUNT(*) as columns_added FROM information_schema.columns
WHERE table_name = 'reports' AND column_name = 'external_id';

COMMIT;
```

**Key Requirements**:
- All SQL operations wrapped in `BEGIN;` and `COMMIT;`
- Clear comments explaining the purpose
- Verify steps to ensure migration worked
- No `DROP` statements without careful consideration
- No `TRUNCATE` of production tables

## Common Migration Types

### 1. Adding a Column

```sql
BEGIN;

ALTER TABLE reports
ADD COLUMN processing_duration_ms INTEGER;

ALTER TABLE reports
ADD CONSTRAINT valid_duration CHECK (processing_duration_ms > 0);

COMMIT;
```

### 2. Creating an Index

```sql
BEGIN;

CREATE INDEX idx_analyses_sentiment_date
ON analyses(sentiment, created_at DESC)
WHERE sentiment IS NOT NULL;

COMMIT;
```

### 3. Adding a Constraint

```sql
BEGIN;

ALTER TABLE notifications
ADD CONSTRAINT max_retries_exceeded
CHECK (retry_count <= max_retries);

COMMIT;
```

### 4. Creating a New Table

```sql
BEGIN;

CREATE TABLE report_metadata_v2 (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    metadata_type VARCHAR(50) NOT NULL,
    metadata_value JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_report_metadata_report_id ON report_metadata_v2(report_id);

GRANT SELECT, INSERT, UPDATE ON report_metadata_v2 TO trading_user;

COMMIT;
```

### 5. Modifying a Constraint

```sql
BEGIN;

-- Drop old constraint
ALTER TABLE analyses DROP CONSTRAINT valid_confidence;

-- Add new constraint with different range
ALTER TABLE analyses
ADD CONSTRAINT valid_confidence_decimal CHECK (confidence_score BETWEEN 0.0 AND 1.0);

COMMIT;
```

## Migration Execution

### Manual Execution

```bash
# Run a single migration
psql -U postgres -d trading_reports -f postgres/migrations/2025_11_26_09_00_example.sql

# Run all migrations in order
for file in postgres/migrations/*.sql; do
    psql -U postgres -d trading_reports -f "$file"
done
```

### Automated Execution

For production deployments, use a migration runner:

```python
import os
import psycopg2
from pathlib import Path

def run_migrations():
    migrations_dir = Path("postgres/migrations")
    migration_files = sorted(migrations_dir.glob("*.sql"))

    conn = psycopg2.connect(
        dbname="trading_reports",
        user="postgres",
        password=os.getenv("POSTGRES_PASSWORD")
    )

    try:
        for migration_file in migration_files:
            with open(migration_file) as f:
                cursor = conn.cursor()
                cursor.execute(f.read())
                conn.commit()
                print(f"Executed: {migration_file.name}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migrations()
```

## Zero-Downtime Deployments

For production systems without downtime:

### 1. Add Column with Default
```sql
BEGIN;

-- Column with NULL default (allows in-place expansion)
ALTER TABLE reports ADD COLUMN new_field TEXT DEFAULT NULL;

-- Populate existing rows in background (if needed)
-- UPDATE reports SET new_field = default_value WHERE new_field IS NULL;

-- Later: add constraint when all rows are populated
-- ALTER TABLE reports ALTER COLUMN new_field SET NOT NULL;

COMMIT;
```

### 2. Create Index Concurrently
```sql
-- Doesn't lock table for writes (takes longer to build)
CREATE INDEX CONCURRENTLY idx_reports_new_field ON reports(new_field);
```

### 3. Backward-Compatible Renames
```sql
BEGIN;

-- Rename old column
ALTER TABLE reports RENAME COLUMN old_name TO old_name_deprecated;

-- Create view for backward compatibility
CREATE VIEW reports_v1 AS
SELECT
    id, email_from, old_name_deprecated as old_name, ...
FROM reports;

COMMIT;
```

## Rollback Procedures

### Rollback Manual Migration

If a migration fails or causes issues, create a rollback migration:

```sql
-- File: 2025_11_26_10_30_rollback_previous_migration.sql
-- Rollback for: 2025_11_26_10_15_add_metadata_column.sql

BEGIN;

-- Remove the changes from the previous migration
ALTER TABLE reports DROP COLUMN metadata CASCADE;

-- Verify rollback
SELECT COUNT(*) FROM information_schema.columns
WHERE table_name = 'reports' AND column_name = 'metadata';

COMMIT;
```

### Rollback Strategy

1. **Never destructive in production** - Archive data before dropping columns
2. **Test in staging first** - Always test migrations on a copy of production
3. **Document rollback plan** - Include rollback steps in migration file
4. **Keep migrations small** - Single logical change per file
5. **Verify before production** - Run in staging environment first

## Testing Migrations

### Test in Docker
```bash
# Create test database container
docker run -d --name test-db \
    -e POSTGRES_PASSWORD=test_pass \
    -e POSTGRES_DB=test_trading_reports \
    postgres:16.1-alpine

# Apply current schema
docker exec test-db psql -U postgres -d test_trading_reports \
    < agent-os/specs/2025-11-25-postgresql-schema-data-persistence/planning/database_schema.sql

# Test new migration
docker exec test-db psql -U postgres -d test_trading_reports \
    < postgres/migrations/2025_11_26_09_00_test_migration.sql

# Verify results
docker exec test-db psql -U postgres -d test_trading_reports -c "SELECT * FROM information_schema.tables WHERE table_schema='public';"

# Cleanup
docker stop test-db && docker rm test-db
```

### Test Before/After
```python
import psycopg2

def test_migration():
    # Before
    conn = psycopg2.connect("...")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reports")
    before_count = cursor.fetchone()[0]
    conn.close()

    # Run migration
    import subprocess
    subprocess.run(["psql", "-U", "postgres", "-d", "trading_reports",
                   "-f", "postgres/migrations/test.sql"])

    # After
    conn = psycopg2.connect("...")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reports")
    after_count = cursor.fetchone()[0]

    assert before_count == after_count, "Row count changed unexpectedly"
    conn.close()
```

## Monitoring Migrations

### Track Applied Migrations

Create a migrations tracking table:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    execution_time_ms INTEGER
);

-- Log successful migration
INSERT INTO schema_migrations (filename, execution_time_ms)
VALUES ('2025_11_26_09_00_example.sql', 1500);

-- List applied migrations
SELECT filename, applied_at FROM schema_migrations ORDER BY applied_at;
```

### Verify Schema Consistency

```sql
-- After major migrations, verify schema
SELECT
    table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_schema = 'public'
GROUP BY table_name
ORDER BY table_name;
```

## Best Practices

1. **One logical change per migration** - Don't combine multiple unrelated changes
2. **Test in staging first** - Never run untested migrations in production
3. **Keep migrations small and fast** - Large migrations lock tables longer
4. **Use descriptive names** - Future developers should understand the change from filename
5. **Include verification steps** - Add SELECT statements to verify migration worked
6. **Document assumptions** - Comment on why a change was needed
7. **Avoid breaking changes** - Keep backward compatibility when possible
8. **Review before applying** - Have another team member review major migrations
9. **Schedule carefully** - Apply during maintenance windows when possible
10. **Monitor performance** - Check query performance after migrations

## Migration Examples

### Add New Feature Column
```sql
-- File: 2025_11_27_11_00_add_broker_confidence_rating.sql
-- Purpose: Store broker confidence rating from market analysis

BEGIN;

ALTER TABLE analyses
ADD COLUMN broker_confidence_rating DECIMAL(3, 2);

ALTER TABLE analyses
ADD CONSTRAINT valid_broker_confidence CHECK (
    broker_confidence_rating IS NULL OR
    broker_confidence_rating BETWEEN 0 AND 1
);

CREATE INDEX idx_analyses_broker_confidence
ON analyses(broker_confidence_rating)
WHERE broker_confidence_rating IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN analyses.broker_confidence_rating IS
    'Confidence rating of broker analysis (0.0 to 1.0)';

COMMIT;
```

### Fix Constraint
```sql
-- File: 2025_11_27_12_00_fix_api_cost_constraint.sql
-- Purpose: Allow NULL api_cost for analyses without cost tracking

BEGIN;

-- Drop old constraint
ALTER TABLE analyses DROP CONSTRAINT valid_tokens;

-- Add new constraint (tokens can be NULL if no API used)
ALTER TABLE analyses
ADD CONSTRAINT valid_tokens CHECK (tokens_used IS NULL OR tokens_used > 0);

COMMIT;
```

### Add Performance Index
```sql
-- File: 2025_11_27_13_00_add_report_status_date_index.sql
-- Purpose: Speed up queries filtering by status and date

BEGIN;

CREATE INDEX CONCURRENTLY idx_reports_status_date
ON reports(status, created_at DESC)
WHERE status != 'archived';

-- Analyze table to update statistics
ANALYZE reports;

COMMIT;
```

## Related Documentation

- Database schema: See `postgres/README.md`
- Backend standards: See `agent-os/standards/backend/migrations.md`
- Production deployment: See `CLAUDE.md` database section

## Support

For migration issues:
1. Check logs: `docker-compose logs postgres`
2. Review schema: `\d reports` in psql
3. Test rollback in staging
4. Contact development team with migration filename and error
