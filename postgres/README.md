# PostgreSQL Database for Trading Report Automation

This directory contains the database schema, initialization scripts, tests, and operational procedures for the PostgreSQL database that powers the trading report automation system.

## Quick Start

### 1. Initialize the Database

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set POSTGRES_PASSWORD
nano .env

# Start PostgreSQL and initialize schema
make dev              # Start services with visible logs
# OR
make prod             # Start services in background
```

### 2. Verify Installation

```bash
# Check database health
make db-health

# Open PostgreSQL shell as trading_user
make db-shell
```

### 3. Load Sample Data (Optional)

```bash
# Connect to database and load sample data
docker-compose exec postgres psql -U trading_user -d trading_reports -f /docker-entrypoint-initdb.d/sample_data.sql

# Or via make (requires psql installed locally)
# docker-compose exec -T postgres psql -U postgres -d trading_reports < postgres/sample_data.sql
```

## Directory Structure

```
postgres/
├── init_database.py              # Database initialization script (Python)
├── sample_data.sql              # Sample test data
├── README.md                    # This file
├── tests/
│   ├── conftest.py             # Pytest fixtures and configuration
│   ├── test_schema_structure.py # Schema validation tests (5-7 tests)
│   └── test_data_flow.py        # Data flow integration tests (6-8 tests)
├── maintenance/
│   ├── vacuum_analyze.sh        # Periodic maintenance script
│   ├── archive_logs.sql         # Log retention management
│   ├── slow_queries.sql         # Performance monitoring
│   └── check_stuck_reports.sql  # Operational health checks
├── backup/
│   ├── backup.sh                # Database backup script
│   └── restore.sh               # Database recovery script
└── monitoring/
    ├── health_check.sql         # Connection and health status
    ├── processing_stats.sql     # Report processing metrics
    ├── notification_delivery.sql# Notification success rates
    ├── disk_usage.sql           # Storage and growth analysis
    └── active_connections.sql   # Connection pool monitoring
```

## Schema Overview

The database consists of 5 main tables:

### 1. **reports** - Central table for all trading reports
- Stores email metadata and report content
- Tracks processing status and retry attempts
- Primary key: `id` (UUID)
- Unique constraint: `email_message_id` (prevents duplicate ingestion)
- Key columns: `status`, `retry_count`, `processed_at`

**Status values**: `pending`, `processing`, `completed`, `failed`

```sql
-- Example: Insert report from email webhook
INSERT INTO reports (
    email_from, email_subject, email_message_id,
    email_received_at, report_url, status
) VALUES (
    'reports@broker.com', 'Daily Report', '<msg@broker.com>',
    NOW(), 'https://broker.com/report/123', 'pending'
) RETURNING id;
```

### 2. **report_images** - Images and charts from reports
- Stores image URLs and metadata
- Supports both external URLs and inline BLOB data
- Foreign key: `report_id` → `reports.id` (ON DELETE CASCADE)
- Includes deduplication via `image_hash` (SHA256)

```sql
-- Example: Insert report chart image
INSERT INTO report_images (
    report_id, image_url, image_type, mime_type, width, height
) VALUES (
    '[report_id]', 'https://broker.com/chart.png', 'chart', 'image/png', 1024, 768
);
```

### 3. **analyses** - AI analysis results for each report
- Stores AI provider info (Anthropic or Groq)
- Contains analysis results: summary, key_trades (JSONB array), sentiment
- Tracks metrics: confidence_score, win_rate, profit_loss, total_trades
- Records API usage: tokens_used, api_cost, processing_time_ms
- One analysis per report (not versioned)
- Foreign key: `report_id` → `reports.id` (ON DELETE CASCADE)

```sql
-- Example: Insert analysis from AI service
INSERT INTO analyses (
    report_id, ai_provider, model_used, summary,
    key_trades, sentiment, confidence_score,
    tokens_used, api_cost, processing_time_ms
) VALUES (
    '[report_id]', 'anthropic', 'claude-3-5-sonnet-20241022',
    'Gold showing bullish momentum...',
    '[{"symbol": "XAUUSD", "entry": 2695.50, ...}]'::jsonb,
    'bullish', 0.87,
    1247, 0.0312, 2150
);
```

### 4. **notifications** - Delivery tracking for analysis notifications
- Tracks email and Telegram delivery status
- One record per channel per analysis
- Status values: `pending`, `sent`, `failed`, `retrying`
- Supports retry logic with `retry_count` and `max_retries`
- Foreign key: `analysis_id` → `analyses.id` (ON DELETE CASCADE)

```sql
-- Example: Create email and telegram notifications
INSERT INTO notifications (
    analysis_id, channel, recipient, status
) VALUES
    ('[analysis_id]', 'email', 'trader@example.com', 'pending'),
    ('[analysis_id]', 'telegram', '123456789', 'pending');
```

### 5. **system_logs** - Audit trail and operational logging
- Event-based logging (not per-action timestamps)
- Includes service_name, log_level, message, and JSONB metadata
- Supports distributed tracing via `correlation_id`
- Optional reference to `report_id` for tracing
- Retention: 30 days in active table, archive older logs
- Foreign key: `report_id` → `reports.id` (ON DELETE SET NULL)

```sql
-- Example: Log scraping completion event
INSERT INTO system_logs (
    service_name, log_level, message, report_id, correlation_id,
    metadata
) VALUES (
    'scraper_service', 'INFO', 'Report scraping completed',
    '[report_id]', '12345678-1234-1234-1234-123456789012',
    '{"duration_ms": 3200, "images_found": 2}'::jsonb
);
```

## Views for Common Queries

### vw_reports_with_analysis
Joins reports with their analyses and image/notification counts for dashboards.

```sql
SELECT id, email_from, status, sentiment, image_count, notification_count
FROM vw_reports_with_analysis
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

### vw_notification_stats
Aggregates notification delivery statistics by channel and status.

```sql
SELECT channel, status, COUNT(*) as count, AVG(retry_count)
FROM vw_notification_stats
GROUP BY channel, status;
```

### vw_daily_metrics
Daily processing metrics for monitoring dashboards.

```sql
SELECT date, total_reports, completed, failed, avg_processing_time_seconds
FROM vw_daily_metrics
WHERE date > CURRENT_DATE - 30;
```

## Complete Report Lifecycle

```
1. EMAIL RECEIVED
   └─> reports table created (status='pending')

2. SCRAPER PROCESSES
   └─> status='processing'
   └─> raw_content populated
   └─> report_images created
   └─> status='completed' (if successful) or 'failed' (if error)

3. AI ANALYZER PROCESSES
   └─> analyses record created
   └─> sentiment and key_trades extracted
   └─> processed_at timestamp set automatically (trigger)

4. NOTIFICATION SERVICE SENDS
   └─> notifications created (one per channel)
   └─> status='sent' or 'retrying' or 'failed'

5. OPTIONAL: ARCHIVAL (after 2 years)
   └─> status='archived' (if configured)
```

## State Transitions

### Report Status Flow
```
pending → processing → completed → archived (optional)
         ↓
      [error] → failed
      [retry?] → back to processing
```

### Notification Status Flow
```
pending → sent (terminal)
       → retrying (with exponential backoff)
       → failed (terminal)
```

## Retry Logic

### Report Retries
- **Max retries**: 3 for scraper, 5 for analyzer
- **Retry window**: 24 hours from report creation
- **Backoff**: Exponential (2^retry_count seconds)
- **Example**: Retry at 2s, 4s, 8s, 16s, ...
- **Max age**: Reports > 24 hours old skip further retries

### Notification Retries
- **Max retries**: 3 (configurable per notification)
- **Backoff**: Exponential (2^retry_count seconds)
- **Status**: 'retrying' while in progress, 'failed' if max exceeded

```sql
-- Check if report should retry
SELECT id, retry_count, created_at FROM reports
WHERE status = 'failed'
  AND retry_count < 3
  AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY last_retry_at ASC;
```

## Custom Data Types (ENUMs)

```sql
-- Report processing status
report_status: 'pending', 'processing', 'completed', 'failed'

-- Notification channels
notification_channel: 'email', 'telegram'

-- Notification delivery status
notification_status: 'pending', 'sent', 'failed', 'retrying'

-- AI provider
ai_provider: 'anthropic', 'groq'

-- Market sentiment
sentiment: 'bullish', 'bearish', 'neutral', 'mixed'
```

## Indexes for Query Performance

**Key Indexes**:
- `idx_reports_created_at` - Chronological queries
- `idx_reports_status` - Active report filtering (partial)
- `idx_analyses_report_id` - Report-to-analysis joins
- `idx_notifications_status` - Pending notification queries (partial)
- `idx_reports_content_search` - Full-text search (GIN)
- `idx_logs_report_id` - Audit trail queries (partial)

## Constraints and Validation

All tables include CHECK constraints for data integrity:

```sql
-- URL validation
CONSTRAINT valid_url CHECK (report_url ~* '^https?://')

-- Confidence score (0-1)
CONSTRAINT valid_confidence CHECK (confidence_score BETWEEN 0 AND 1)

-- Retry counts (non-negative)
CONSTRAINT valid_retry CHECK (retry_count >= 0)

-- Win rate (0-100%)
CONSTRAINT valid_win_rate CHECK (win_rate BETWEEN 0 AND 100)
```

## Triggers and Functions

### update_updated_at_column()
Automatically updates `updated_at` on record modification.
- Applied to: `reports`, `notifications`

### set_processed_at()
Automatically sets `processed_at` when status becomes `'completed'`.
- Applied to: `reports`

## Common Query Patterns

### Find pending reports (for scraper)
```sql
SELECT id, report_url FROM reports
WHERE status IN ('pending', 'processing')
  AND retry_count < 3
  AND (last_retry_at IS NULL OR last_retry_at < NOW() - INTERVAL '1 hour')
ORDER BY created_at ASC
LIMIT 10;
```

### Get report with analysis (for notifications)
```sql
SELECT r.id, r.email_from, a.summary, a.sentiment, a.key_trades
FROM reports r
LEFT JOIN analyses a ON r.id = a.report_id
WHERE r.id = $1;
```

### Find stuck reports (operational monitoring)
```sql
SELECT id, email_subject, status, created_at,
       EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600 as age_hours
FROM reports
WHERE status = 'processing'
  AND created_at < NOW() - INTERVAL '24 hours'
ORDER BY created_at ASC;
```

### Search reports by keyword (full-text search)
```sql
SELECT id, email_subject, email_from
FROM reports
WHERE to_tsvector('english', raw_content) @@ to_tsquery('english', 'gold | silver')
ORDER BY ts_rank_cd(to_tsvector('english', raw_content), to_tsquery('english', 'gold | silver')) DESC;
```

### Query JSONB metadata
```sql
-- Find reports by broker
SELECT id, email_subject FROM reports
WHERE metadata->>'broker' = 'XM'
  AND created_at > NOW() - INTERVAL '30 days';

-- Query trade details
SELECT r.id, json_array_elements(a.key_trades) as trade
FROM analyses a
JOIN reports r ON a.report_id = r.id
WHERE a.key_trades @> '[{"symbol": "XAUUSD"}]'::jsonb;
```

### Distributed tracing via correlation_id
```sql
SELECT created_at, service_name, log_level, message
FROM system_logs
WHERE correlation_id = '12345678-1234-1234-1234-123456789012'
ORDER BY created_at ASC;
```

## Testing

### Run Schema Validation Tests
```bash
# Test that all schema elements exist and are correct
make test-schema

# Or manually
python -m pytest postgres/tests/test_schema_structure.py -v
```

### Run Data Flow Tests
```bash
# Test complete report lifecycle and data integrity
make test-data

# Or manually
python -m pytest postgres/tests/test_data_flow.py -v
```

### Run All Tests
```bash
make test
```

### Load Sample Data
```sql
psql -U trading_user -d trading_reports < postgres/sample_data.sql
```

## Operational Tasks

### Database Backup
```bash
# Create backup (automated cleanup of old backups)
make db-backup BACKUP_FILE=trading_reports_backup.sql

# List available backups
ls -lh backups/
```

### Database Restore
```bash
# Restore from backup (interactive confirmation)
make db-restore BACKUP_FILE=backups/trading_reports_20251125_120000.sql
```

### Maintenance and Optimization
```bash
# Vacuum and analyze tables
make db-vacuum

# Check database health
make db-health

# View processing statistics
docker-compose exec postgres psql -U postgres -d trading_reports -f postgres/monitoring/processing_stats.sql

# Monitor connections
docker-compose exec postgres psql -U postgres -d trading_reports -f postgres/monitoring/active_connections.sql

# Archive old logs
make db-logs-archive
```

### Performance Monitoring
```bash
# Check slow queries (requires pg_stat_statements)
docker-compose exec postgres psql -U postgres -d trading_reports -f postgres/monitoring/slow_queries.sql

# Monitor disk usage
docker-compose exec postgres psql -U postgres -d trading_reports -f postgres/monitoring/disk_usage.sql

# Check for stuck reports
docker-compose exec postgres psql -U postgres -d trading_reports -f postgres/maintenance/check_stuck_reports.sql
```

## Configuration

### Environment Variables
See `.env.example` for complete list. Key variables:

```bash
POSTGRES_USER=postgres              # Superuser for initialization
POSTGRES_PASSWORD=secure_password   # Required for Docker
POSTGRES_HOST=postgres              # Container name or localhost
POSTGRES_PORT=5432                  # PostgreSQL port
TRADING_USER_PASSWORD=user_password # Application user password
LOG_RETENTION_DAYS=30              # Days to keep active logs
```

### Connection String
```
postgresql://trading_user:password@localhost:5432/trading_reports?sslmode=require
```

## Troubleshooting

### Connection Issues
```bash
# Test PostgreSQL connectivity
docker-compose exec postgres pg_isready -U postgres

# Check logs
docker-compose logs postgres

# Verify database exists
docker-compose exec postgres psql -U postgres -l
```

### Schema Issues
```bash
# Verify all tables exist
make db-health

# Reconnect and reinitialize (careful - destructive!)
make clean && make dev
```

### Performance Issues
```bash
# Check for table bloat (dead rows)
docker-compose exec postgres psql -U postgres -d trading_reports -f postgres/monitoring/disk_usage.sql

# Run maintenance
make db-vacuum

# Check slow queries
docker-compose exec postgres psql -U postgres -d trading_reports -f postgres/monitoring/slow_queries.sql
```

### Stuck Reports
```bash
# Find processing reports older than 24 hours
docker-compose exec postgres psql -U postgres -d trading_reports -f postgres/maintenance/check_stuck_reports.sql

# Manual fix: mark as failed
docker-compose exec postgres psql -U postgres -d trading_reports -c \
  "UPDATE reports SET status='failed', error_message='Manual reset' WHERE id='[id]';"
```

## Maintenance Schedule

### Daily
- Backup database: `make db-backup`
- Check health: `make db-health`

### Weekly
- Review stuck reports: `check_stuck_reports.sql`
- Monitor disk usage: `disk_usage.sql`

### Monthly
- Vacuum and analyze: `make db-vacuum`
- Archive old logs: `make db-logs-archive`
- Review slow queries: `slow_queries.sql`
- Review notification delivery: `notification_delivery.sql`

## Security Notes

1. **Never commit credentials** - .env file should be in .gitignore
2. **Use strong passwords** - Generate with: `openssl rand -base64 32`
3. **Enable SSL in production** - Set `sslmode=require` in connection string
4. **Rotate credentials** - Quarterly for database password
5. **Limit permissions** - trading_user has SELECT, INSERT, UPDATE, DELETE only
6. **Audit logging** - All changes tracked in system_logs table

## Future Enhancements

- [ ] Read-only analytics user for dashboards
- [ ] Automatic log archival to cold storage (S3)
- [ ] Materialized views for expensive aggregations
- [ ] Table partitioning if reports exceed 10M records
- [ ] Replication for high availability

## Support & Documentation

- Database schema: See `agent-os/specs/2025-11-25-postgresql-schema-data-persistence/spec.md`
- API standards: See `agent-os/standards/backend/api.md`
- Migration guide: See `postgres/migrations/README.md`
- Code standards: See `CLAUDE.md`

## Version History

- v1.0 - Initial schema (2025-11-25)
  - 5 tables (reports, report_images, analyses, notifications, system_logs)
  - 3 views for common queries
  - Full-text search support
  - Audit trail via system_logs
  - Retry logic and state management
