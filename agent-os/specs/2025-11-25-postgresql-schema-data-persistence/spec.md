# Specification: PostgreSQL Schema & Data Persistence

## Goal

Establish a robust, auditable PostgreSQL database layer that stores trading reports from email ingestion through analysis and notification. This is the foundational data store that all other services depend on, providing reliable state management, comprehensive audit trails, and efficient query patterns for the trading report automation system.

## User Stories

- As a trading analyst, I want all my trading reports to be automatically stored and tracked so I can review historical data, retry failed reports, and analyze trends over time
- As a system operator, I want complete audit logging of all data changes so I can debug issues, trace processing workflows, and ensure data integrity
- As an automation service, I want a standardized database with clear state transitions and reliable error handling so I can orchestrate report processing without data loss

## Specific Requirements

**Core Report Storage & Metadata**
- Store each trading report with email metadata (message ID, from, subject, received timestamp) as the primary unique constraint for deduplication
- Capture report title, URL, and raw extracted content in the reports table
- Store report-specific metadata (broker, account, trading pairs, etc.) in JSONB metadata column for schema flexibility
- Maintain created_at, updated_at, and processed_at timestamps on all records for auditing
- Implement URL validation using PostgreSQL constraints (must be http/https)

**Image & Asset Management**
- Store image metadata separately in report_images table (URLs preferred, no direct downloads for TradingView links)
- Support both external URLs and inline image data for flexibility
- Include image hash (SHA256) for deduplication of forwarded reports
- Track image dimensions, file size, MIME type, and sequence order within report
- Allow multiple images per report with sequence ordering
- Use ON DELETE CASCADE to maintain referential integrity

**AI Analysis Storage & Lifecycle**
- Create one analyses record per report (not versioned - one analysis per report, updating over time)
- Store provider information (Anthropic or Groq), model used, and prompt template for reproducibility
- Capture analysis results: summary, key_trades (JSONB array), market_analysis, recommendations
- Extract trading metrics: sentiment, confidence_score, win_rate, profit_loss, total_trades
- Record API usage: tokens_used, api_cost, processing_time_ms for cost tracking
- Use JSONB key_trades column to store individual trade details with flexibility for schema evolution

**Processing State Management**
- Implement linear state progression: pending → processing → completed (or failed at any step)
- Store current status in status column with CHECK constraint (no arbitrary values)
- Track retry_count and last_retry_at for failure recovery
- Store error_message when status is failed for diagnostics
- Set processed_at timestamp automatically when status transitions to completed

**Error Handling & Retry Logic**
- Support 3 retries for login/scraping failures (configurable in application logic)
- Support 5 retries for AI analysis failures (configurable in application logic)
- Enforce 24-hour maximum window for retries before marking report as permanently failed
- Log all retry attempts with timestamps for forensics
- When max retries exceeded, send email to operator with report URL for manual review

**Notification Tracking & Delivery**
- Create notifications records for each analysis that needs delivery (one per channel: email and/or Telegram)
- Track notification status: pending → sent (or failed/retrying)
- Store external message IDs (Telegram message ID, email message ID) for delivery tracking
- Implement max_retries (default 3) with validation constraint
- Store message_content for audit trail and debugging
- Automatically update updated_at timestamp on status changes

**Audit Logging & Event Trail**
- Implement event-based logging in system_logs table (not timestamp per action, but descriptive events)
- Log key business events: report received, scraping started/completed, analysis started/completed, notification sent/failed
- Include service_name, log_level, message, and correlation_id for distributed tracing
- Store stack_trace for exceptions
- Use JSONB metadata for additional context (retry count, duration, resource usage)
- Maintain logs for minimum 30 days, archive older logs per retention policy
- Enable full-text search on report content using PostgreSQL GIN index

**Deduplication & Data Integrity**
- Use email_message_id as primary unique constraint to prevent duplicate ingestion
- Use content_hash (derived from email_message_id + report URL) as secondary deduplication for forwarded reports
- Implement image_hash for image deduplication when same image appears in multiple reports
- Use UUID for primary keys across all tables for distributed system readiness
- Implement CHECK constraints for data validation (URL format, confidence scores 0-1, retry counts >= 0)

**Multi-Service Integration Points**
- Email Webhook Service writes to reports table with email metadata, reads back created report ID
- Scraper Service updates reports status (pending → processing → completed) and stores raw_content
- AI Analyzer Service creates/updates analyses record based on report ID and raw_content
- Notification Service reads analyses, creates notification records, updates status as delivery progresses
- N8N only triggers webhooks (does not write directly to database) for orchestration
- All services use environment variables for database connection string (user, password, host, port, database)

**Views for Common Query Patterns**
- vw_reports_with_analysis: Join reports with their latest analysis and image/notification counts
- vw_notification_stats: Aggregate notification delivery statistics by channel and status
- vw_daily_metrics: Daily report processing metrics (total, completed, failed, average processing time)
- Enable rapid queries for dashboards and monitoring without complex joins in application code

**Indexes for Query Performance**
- Index on reports.created_at DESC for chronological queries
- Index on reports.status for active report filtering (with partial index WHERE status != 'completed')
- Index on reports.email_received_at for date-range queries
- Index on reports.email_from for sender filtering
- Hash index on reports.report_url for exact URL matching
- GIN full-text search index on reports.raw_content for keyword searching
- Composite index on report_images(report_id, sequence_order) for ordered image retrieval
- Indexes on all foreign keys and common filter columns for join performance

**PostgreSQL Version & Extensions**
- Require PostgreSQL 15+ (specified as 16.1+ in schema)
- Enable uuid-ossp extension for UUID generation
- Enable pg_trgm extension for trigram text search optimization
- Use custom ENUM types for constrained values (report_status, notification_channel, etc.)
- Implement database functions and triggers for automatic timestamp management

**Security & Encryption**
- Sensitive credentials (email passwords, API keys) never stored in database - use environment variables or secrets vault
- PostgreSQL connection requires SSL/TLS in production
- Database user (trading_user) created with minimal required permissions (SELECT, INSERT, UPDATE, DELETE on tables only)
- No direct access to production database for developers - use read-only replica for queries
- Store salted hashes for any authentication data (not needed for current single-user system, but maintain capability)

**Data Retention & Archival**
- Keep active reports (status != 'archived') in primary tables indefinitely
- Archive completed reports after 2 years (status = 'archived') or configure per business policy
- System logs retention: 30 days in active table, archive older logs to separate log_archive table
- Implement archive_reports stored procedure for periodic maintenance
- Maintain foreign key relationships during archival process

## Visual Design

(No visual mockups provided for database schema specification)

## Existing Code to Leverage

**database_schema.sql - Complete PostgreSQL Schema**
- Complete, production-ready schema with all tables, indexes, views, functions, and triggers already defined
- Includes comprehensive CHECK constraints for data validation
- Features automatic timestamp management via update_updated_at_column() trigger function
- Implements automatic processed_at timestamp on status completion via set_processed_at() trigger function
- Contains three reporting views (vw_reports_with_analysis, vw_notification_stats, vw_daily_metrics) for common queries
- Provides full-text search capability on report content using GIN indexes
- Defines custom ENUM types for status, channels, providers, and sentiment
- Can be directly applied to initialize the database (no modifications needed for core functionality)
- Includes permission grants for trading_user database role
- Comments on all tables and indexes for maintainability

## Core Entities & Detailed Schema

### Reports Table

The central table storing trading report metadata and raw content. Represents the lifecycle of a report from email ingestion to analysis completion.

**Primary Purpose:** Track all trading reports through their processing pipeline with state management and error handling.

**Key Columns:**
- `id UUID`: Unique identifier for the report, generated via uuid_generate_v4()
- `email_received_at TIMESTAMPTZ`: When the email containing the report was received (from email headers)
- `email_subject TEXT`: Subject line of the email
- `email_from TEXT`: Sender email address for filtering and audit trail
- `email_message_id TEXT UNIQUE`: Unique message ID from email headers (RFC 5322) - PRIMARY deduplication constraint
- `report_url TEXT NOT NULL`: Direct link to the trading report (must be validated as http/https)
- `report_title TEXT`: Extracted title from the report webpage
- `raw_content TEXT`: Complete extracted text content from the report (can be very large)
- `status report_status DEFAULT 'pending'`: Current processing state (pending | processing | completed | failed)
- `error_message TEXT`: Description of failure reason if status = failed
- `retry_count INTEGER DEFAULT 0`: Number of retry attempts made (starts at 0)
- `last_retry_at TIMESTAMPTZ`: Timestamp of most recent retry attempt
- `metadata JSONB DEFAULT '{}'`: Flexible JSON field for broker, account, trading pair, symbols extracted, etc.
- `created_at TIMESTAMPTZ DEFAULT NOW()`: Report creation timestamp
- `updated_at TIMESTAMPTZ DEFAULT NOW()`: Last modification timestamp (auto-updated via trigger)
- `processed_at TIMESTAMPTZ`: Timestamp when status transitions to completed (auto-set via trigger)

**Constraints:**
- PRIMARY KEY: id
- UNIQUE: email_message_id (ensures no duplicate emails create multiple reports)
- CHECK: report_url ~* '^https?://' (validates URL format)
- CHECK: retry_count >= 0 (prevents negative retry counts)
- FOREIGN KEY: None (reports are root entity)

**Relationships:**
- ONE → MANY: One report has many report_images (cascade delete)
- ONE → MANY: One report has many analyses (cascade delete)
- ONE → MANY: One report may appear in many system_logs (set NULL on delete)

**Triggers Applied:**
- update_reports_updated_at: Sets updated_at to NOW() before UPDATE
- set_report_processed_at: Sets processed_at to NOW() when status transitions to completed

**Indexes:**
- idx_reports_created_at: (created_at DESC) - For chronological queries
- idx_reports_status: (status) WHERE status != 'completed' - Partial index for active reports
- idx_reports_email_received: (email_received_at DESC) - For date-range email queries
- idx_reports_email_from: (email_from) - For sender filtering
- idx_reports_url: USING hash(report_url) - For exact URL matching
- idx_reports_content_search: USING gin(to_tsvector('english', raw_content)) - Full-text search

### Report Images Table

Stores images, charts, and visual assets extracted from or referenced by trading reports.

**Primary Purpose:** Maintain inventory of trading-related visuals with metadata for display and deduplication.

**Key Columns:**
- `id UUID`: Unique identifier for the image record
- `report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE`: Links to parent report
- `image_url TEXT`: URL to external image (preferred for TradingView links, stored as reference only)
- `image_data BYTEA`: Optional inline image data (for images embedded in email)
- `image_hash TEXT`: SHA256 hash of image content for deduplication of forwarded reports
- `image_type VARCHAR(50) DEFAULT 'screenshot'`: Classification (screenshot, chart, tradingview_link, indicator, etc.)
- `mime_type VARCHAR(100)`: Content type (image/png, image/jpeg, text/html for links, etc.)
- `width INTEGER`: Image width in pixels
- `height INTEGER`: Image height in pixels
- `size_bytes INTEGER`: File size of image data (if stored inline)
- `sequence_order INTEGER DEFAULT 0`: Order within report for proper display sequence
- `metadata JSONB DEFAULT '{}'`: Additional data (alt_text, description, extracted_text, tradingview_symbol, etc.)
- `created_at TIMESTAMPTZ DEFAULT NOW()`: When image record was created

**Constraints:**
- PRIMARY KEY: id
- FOREIGN KEY: report_id → reports(id) ON DELETE CASCADE
- CHECK: (image_url IS NOT NULL) OR (image_data IS NOT NULL) - Must have URL or data
- CHECK: (width IS NULL AND height IS NULL) OR (width > 0 AND height > 0) - Dimensions valid if present

**Design Decisions:**
- Prefer URLs over data storage (BYTEA) to minimize database size
- TradingView links stored as URLs only (image_url), not downloaded
- Support both embedded and external images for flexibility
- Use image_hash for deduplication when same report forwarded multiple times
- sequence_order allows reconstruction of original report layout
- JSONB metadata stores extracted text from images (via OCR if implemented later)

**Indexes:**
- idx_images_report_id: (report_id) - For joining images to report
- idx_images_hash: (image_hash) WHERE image_hash IS NOT NULL - For deduplication
- idx_images_sequence: (report_id, sequence_order) - For ordered retrieval

### Analyses Table

Stores AI-generated analysis results for each trading report. One analysis record per report (not versioned).

**Primary Purpose:** Maintain AI analysis artifacts (summaries, insights, sentiment, trading metrics) with provider tracking for reproducibility.

**Key Columns:**
- `id UUID`: Unique identifier for the analysis record
- `report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE`: Links to the report being analyzed
- `ai_provider ai_provider NOT NULL`: Which AI provider was used (anthropic | groq)
- `model_used VARCHAR(100) NOT NULL`: Specific model identifier (claude-3-sonnet, groq-llama, etc.)
- `prompt_template TEXT`: The prompt template used for reproducibility and auditing
- `summary TEXT NOT NULL`: AI-generated executive summary of the trading report
- `key_trades JSONB DEFAULT '[]'`: Array of objects containing individual trade details:
  ```json
  [
    {
      "symbol": "EURUSD",
      "entry_price": 1.0850,
      "exit_price": 1.0920,
      "profit_loss": 0.0070,
      "timeframe": "4H",
      "trade_type": "long"
    }
  ]
  ```
- `market_analysis TEXT`: Broader market context and analysis from AI
- `recommendations TEXT`: AI-suggested trading recommendations based on report
- `sentiment sentiment`: Overall market sentiment classification (bullish | bearish | neutral | mixed)
- `confidence_score DECIMAL(3,2)`: Confidence in sentiment analysis (0.00 to 1.00)
- `win_rate DECIMAL(5,2)`: Extracted win rate percentage from report (0-100)
- `profit_loss DECIMAL(15,2)`: Extracted profit/loss amount from report (can be negative)
- `total_trades INTEGER`: Total number of trades in report
- `tokens_used INTEGER`: AI API tokens consumed for cost tracking
- `api_cost DECIMAL(10,4)`: Calculated cost of AI analysis call
- `processing_time_ms INTEGER`: Duration of AI analysis in milliseconds
- `metadata JSONB DEFAULT '{}'`: Additional data (model_settings, prompt_version, extraction_confidence, etc.)
- `created_at TIMESTAMPTZ DEFAULT NOW()`: When analysis was created

**Constraints:**
- PRIMARY KEY: id
- FOREIGN KEY: report_id → reports(id) ON DELETE CASCADE
- CHECK: confidence_score BETWEEN 0 AND 1 (validates 0-100 percentage as decimal)
- CHECK: tokens_used > 0 (must have used some tokens)
- CHECK: win_rate BETWEEN 0 AND 100 (percentage bounds)

**Design Decisions:**
- One analysis per report (not versioned) to maintain simplicity and clear audit trail
- JSONB key_trades allows flexible trade details without schema changes
- Store provider and model for auditing which AI generated which analysis
- Capture full prompt_template for reproducibility and debugging
- Record all cost metrics (tokens, cost, processing time) for resource optimization
- sentiment and confidence_score provide ML explainability
- Allow NULL for extracted metrics if not present in report

**Indexes:**
- idx_analyses_report_id: (report_id) - For joining to reports
- idx_analyses_created_at: (created_at DESC) - For chronological queries
- idx_analyses_sentiment: (sentiment) WHERE sentiment IS NOT NULL - For sentiment filtering
- idx_analyses_provider: (ai_provider) - For provider-specific queries
- idx_analyses_key_trades: USING gin(key_trades) - For querying trade arrays

### Notifications Table

Tracks sending of analysis results via email and Telegram. One record per channel per analysis.

**Primary Purpose:** Maintain delivery status and retry history for multi-channel notification of analysis results.

**Key Columns:**
- `id UUID`: Unique identifier for the notification record
- `analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE`: Links to analysis being delivered
- `channel notification_channel NOT NULL`: Delivery method (telegram | email)
- `recipient TEXT NOT NULL`: Phone number/chat ID (Telegram) or email address (email)
- `status notification_status DEFAULT 'pending'`: Current delivery state (pending | sent | failed | retrying)
- `sent_at TIMESTAMPTZ`: When notification was successfully delivered
- `error_message TEXT`: Description of delivery failure if status = failed
- `retry_count INTEGER DEFAULT 0`: Number of delivery attempts made
- `max_retries INTEGER DEFAULT 3`: Maximum retries allowed before marking as failed
- `message_id TEXT`: External message ID for tracking (Telegram message_id or email Message-ID)
- `message_content TEXT`: Full text of message sent (for audit trail and debugging)
- `metadata JSONB DEFAULT '{}'`: Additional data (delivery_latency_ms, failure_reason, retry_schedule, etc.)
- `created_at TIMESTAMPTZ DEFAULT NOW()`: When notification was created
- `updated_at TIMESTAMPTZ DEFAULT NOW()`: Last modification timestamp (auto-updated via trigger)

**Constraints:**
- PRIMARY KEY: id
- FOREIGN KEY: analysis_id → analyses(id) ON DELETE CASCADE
- CHECK: retry_count >= 0 AND retry_count <= max_retries (validates retry bounds)

**Design Decisions:**
- One record per channel per analysis (email and Telegram are separate notifications)
- External message_id enables tracking in external systems and deduplication
- Store message_content for audit and debugging (what exactly was sent)
- max_retries per notification allows configuration per channel if needed
- metadata JSONB captures delivery latency and failure diagnostics

**Indexes:**
- idx_notifications_analysis_id: (analysis_id) - For finding all notifications for analysis
- idx_notifications_status: (status) WHERE status != 'sent' - Partial index for pending/retrying
- idx_notifications_channel: (channel) - For channel-specific queries
- idx_notifications_created_at: (created_at DESC) - For chronological queries

### System Logs Table

Event-based audit trail for debugging, monitoring, and compliance. Captures key business events with context.

**Primary Purpose:** Provide comprehensive audit trail of all significant system events without per-action timestamps.

**Key Columns:**
- `id UUID`: Unique identifier for the log entry
- `service_name VARCHAR(100) NOT NULL`: Name of service that generated the log (email_webhook, scraper_service, ai_analyzer, notification_service, etc.)
- `log_level VARCHAR(20) NOT NULL`: Log severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `message TEXT NOT NULL`: Descriptive message of the event (e.g., "Report scraping completed in 3.2s", "AI analysis failed after 5 retries")
- `report_id UUID REFERENCES reports(id) ON DELETE SET NULL`: Associated report if applicable
- `user_id TEXT`: Single user (for future multi-user support)
- `correlation_id UUID`: Distributed trace ID for following a report through all services
- `metadata JSONB DEFAULT '{}'`: Event-specific context:
  ```json
  {
    "retry_count": 3,
    "duration_ms": 3200,
    "error_code": "TIMEOUT",
    "service_version": "1.0.0",
    "resource_usage": {"cpu_ms": 500, "memory_mb": 42}
  }
  ```
- `stack_trace TEXT`: Full stack trace if event is an exception
- `created_at TIMESTAMPTZ DEFAULT NOW()`: When event occurred

**Constraints:**
- PRIMARY KEY: id
- FOREIGN KEY: report_id → reports(id) ON DELETE SET NULL

**Design Decisions:**
- Event-based logging (single message) instead of multiple logs per action (reduces log volume)
- metadata JSONB captures duration, retry count, and other context for analysis
- correlation_id enables tracing single report through all services
- service_name identifies which service generated the event
- log_level enables filtering by severity for alerting

**Indexes:**
- idx_logs_created_at: (created_at DESC) - For chronological queries
- idx_logs_service: (service_name) - For service-specific logs
- idx_logs_level: (log_level) - For severity filtering
- idx_logs_report_id: (report_id) WHERE report_id IS NOT NULL - Partial index for report-specific logs

## Data Flow & Lifecycle

### Report Lifecycle: Complete State Progression

```
EMAIL RECEIVED
     ↓
[reports table created with status='pending']
     ↓
SCRAPER TRIGGERED
     ↓
[status='processing', retry_count incremented if retry]
[raw_content populated]
[report_images created if images found]
     ↓
SUCCESS? ─NO─→ [status='failed', error_message set, retry_count++]
     ↓ YES      [log system event with retry metadata]
              [Check if retry_count < 3 AND < 24h old]
[status='processing']  ─YES→ [schedule retry]
     ↓ NO          ─NO→ [send email to operator with manual review link]
AI ANALYZER TRIGGERED
     ↓
[analyses table created]
[metadata populated with model/provider info]
     ↓
AI ANALYSIS COMPLETE
     ↓
SUCCESS? ─NO─→ [status='failed', error_message set]
     ↓ YES      [log system event with tokens_used, api_cost]
              [Check if retry_count < 5 AND < 24h old]
[status='completed'] ─YES→ [schedule retry after exponential backoff]
     ↓ NO          ─NO→ [send email to operator]
NOTIFICATION SERVICE TRIGGERED
     ↓
[notifications created for email and telegram channels]
[message_content generated from analysis summary]
     ↓
SENDING NOTIFICATIONS
     ↓
DELIVERED
     ↓
[notification.status='sent', sent_at=NOW()]
[report.status='completed', processed_at=NOW()]
     ↓
ARCHIVE (optional, after 2 years)
     ↓
[report.status='archived']
[moved to archive tables if configured]
```

### Example: Complete Report Flow

**1. Email Webhook Service Receives Email**
```sql
-- Email webhook service calls: POST /api/webhooks/email
-- Payload contains: from, subject, message_id, received_at

INSERT INTO reports (
  email_from,
  email_subject,
  email_message_id,
  email_received_at,
  report_url,
  status,
  metadata
) VALUES (
  'reports@broker.com',
  'XAU/USD Trading Report - 2025-11-25',
  '<unique-message-id@broker.com>',
  '2025-11-25 09:30:00+00',
  'https://broker.com/reports/20251125',
  'pending',
  '{"broker": "XM", "account": "live", "extracted_from": "email_body"}'
) RETURNING id;
-- Returns: report_id = 550e8400-e29b-41d4-a716-446655440000
```

**2. N8N Webhook Triggers Scraper Service**
```sql
-- Scraper service reads report by ID
SELECT id, report_url, email_subject FROM reports
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

-- Scraper starts Playwright session, extracts content
UPDATE reports
SET status = 'processing',
    updated_at = NOW()
WHERE id = '550e8400-e29b-41d4-a716-446655440000';
```

**3. Scraper Finds Images and Saves to report_images**
```sql
-- Scraper extracted 2 chart images from report
INSERT INTO report_images (
  report_id,
  image_url,
  image_type,
  mime_type,
  width,
  height,
  sequence_order,
  metadata
) VALUES
  (
    '550e8400-e29b-41d4-a716-446655440000',
    'https://broker.com/chart/xauusd-4h.png',
    'chart',
    'image/png',
    1024,
    768,
    0,
    '{"timeframe": "4H", "symbol": "XAUUSD"}'
  ),
  (
    '550e8400-e29b-41d4-a716-446655440000',
    'https://tradingview.com/chart/xauusd/?utm_source=...',
    'tradingview_link',
    'text/html',
    NULL,
    NULL,
    1,
    '{"embedded": true}'
  );
```

**4. Scraper Completes, Updates Report with Content**
```sql
UPDATE reports
SET
  status = 'completed',
  raw_content = 'Gold continued higher today... [full extracted text]...',
  report_title = 'XAU/USD Trading Report - 2025-11-25',
  metadata = jsonb_set(metadata, '{scrape_duration_ms}', '3200')
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

-- Automatic trigger: update_reports_updated_at sets updated_at = NOW()
```

**5. Scraper Service Logs Event**
```sql
INSERT INTO system_logs (
  service_name,
  log_level,
  message,
  report_id,
  correlation_id,
  metadata
) VALUES (
  'scraper_service',
  'INFO',
  'Report scraping completed',
  '550e8400-e29b-41d4-a716-446655440000',
  '12345678-1234-1234-1234-123456789012',
  '{
    "duration_ms": 3200,
    "images_found": 2,
    "content_length_bytes": 45823,
    "tradingview_links": 1
  }'
);
```

**6. AI Analyzer Service Reads Report & Creates Analysis**
```sql
-- AI Analyzer reads report and raw_content
SELECT id, raw_content, report_title FROM reports
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

-- Send raw_content to Anthropic Claude API
-- Receive analysis result

INSERT INTO analyses (
  report_id,
  ai_provider,
  model_used,
  prompt_template,
  summary,
  key_trades,
  sentiment,
  confidence_score,
  win_rate,
  profit_loss,
  total_trades,
  tokens_used,
  api_cost,
  processing_time_ms
) VALUES (
  '550e8400-e29b-41d4-a716-446655440000',
  'anthropic',
  'claude-3-5-sonnet-20241022',
  'v1-trading-analysis',
  'Gold showed bullish momentum today with clean breakout above 2700...',
  '[
    {
      "symbol": "XAUUSD",
      "entry": 2695.50,
      "exit": 2708.30,
      "type": "long",
      "timeframe": "4H",
      "profit_loss": 12.80,
      "status": "closed"
    }
  ]',
  'bullish',
  0.87,
  72.50,
  3850.00,
  8,
  1247,
  0.0312,
  2150
);
```

**7. Notification Service Creates Delivery Records**
```sql
-- Notification service reads analysis
SELECT * FROM analyses WHERE report_id = '550e8400-e29b-41d4-a716-446655440000';

-- Create email and telegram notifications
INSERT INTO notifications (
  analysis_id,
  channel,
  recipient,
  status,
  message_content,
  metadata
) VALUES
  (
    '660e8400-e29b-41d4-a716-446655440111',
    'email',
    'trader@example.com',
    'pending',
    'XAU/USD Trading Report Summary...[full message text]',
    '{"scheduled_send": "2025-11-25T10:00:00Z"}'
  ),
  (
    '660e8400-e29b-41d4-a716-446655440111',
    'telegram',
    '123456789',
    'pending',
    'XAU/USD Report: Bullish sentiment, 8 trades, win rate 72.5%',
    '{"scheduled_send": "2025-11-25T10:00:00Z"}'
  );
```

**8. Email Sent Successfully**
```sql
UPDATE notifications
SET
  status = 'sent',
  sent_at = NOW(),
  message_id = '20251125-100045-smtp@email-service',
  metadata = jsonb_set(metadata, '{delivery_latency_ms}', '450')
WHERE id = '[email notification id]';

-- Automatic trigger: update_notifications_updated_at sets updated_at = NOW()
```

**9. Telegram Sent Successfully**
```sql
UPDATE notifications
SET
  status = 'sent',
  sent_at = NOW(),
  message_id = '7289473829',  -- Telegram message ID
  metadata = jsonb_set(metadata, '{delivery_latency_ms}', '230')
WHERE id = '[telegram notification id]';
```

**10. All Notifications Sent - Mark Report Complete**
```sql
-- Notification service checks all notifications for analysis are sent
SELECT COUNT(*)
FROM notifications n
JOIN analyses a ON n.analysis_id = a.id
WHERE a.report_id = '550e8400-e29b-41d4-a716-446655440000'
  AND n.status != 'sent';
-- Result: 0 (all sent)

-- Update report status to completed
UPDATE reports
SET status = 'completed'
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

-- Automatic trigger: set_report_processed_at sets processed_at = NOW()
```

### Error Handling Flow: Login Failure Example

```sql
-- Scraper service encounters login failure (wrong credentials, portal down, etc.)

UPDATE reports
SET
  status = 'failed',
  retry_count = retry_count + 1,
  last_retry_at = NOW(),
  error_message = 'Login failed: 403 Forbidden (incorrect credentials or temporary lockout)',
  metadata = jsonb_set(
    metadata,
    '{last_error}',
    '"Session expired or credentials invalid"'
  )
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

-- Check if should retry
SELECT retry_count, created_at, status
FROM reports
WHERE id = '550e8400-e29b-41d4-a716-446655440000';
-- Result: retry_count=1, created_at=2025-11-25 09:30:00, status=failed

-- Application logic checks:
-- - retry_count (1) < max_retries (3)? YES
-- - created_at is within 24 hours? YES
-- Decision: SCHEDULE RETRY with exponential backoff (wait 2^1 = 2 minutes)

-- Log the retry attempt
INSERT INTO system_logs (
  service_name,
  log_level,
  message,
  report_id,
  metadata
) VALUES (
  'scraper_service',
  'WARNING',
  'Report scraping failed, scheduled for retry',
  '550e8400-e29b-41d4-a716-446655440000',
  '{
    "retry_count": 1,
    "max_retries": 3,
    "next_retry": "2025-11-25 09:32:00+00",
    "backoff_seconds": 120,
    "error": "Login failed: 403 Forbidden"
  }'
);
```

### Error Recovery: Exceeded Max Retries

```sql
-- After 3 failed login attempts over time, report.retry_count = 3

-- Application logic detects max_retries exceeded
-- Decision: Mark as permanently failed and alert operator

UPDATE reports
SET
  status = 'failed',
  error_message = 'Failed after 3 login attempts over 6 hours. Manual review required.'
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

-- Send manual review notification
-- (Logic in application to compose email with report link)
-- Email body: "Report from reports@broker.com failed processing. Review at:
--             https://dashboard.example.com/reports/550e8400-e29b-41d4-a716-446655440000"

-- Log final failure
INSERT INTO system_logs (
  service_name,
  log_level,
  message,
  report_id,
  metadata
) VALUES (
  'scraper_service',
  'ERROR',
  'Report processing abandoned: max retries exceeded',
  '550e8400-e29b-41d4-a716-446655440000',
  '{
    "retry_count": 3,
    "max_retries": 3,
    "total_duration_hours": 6.5,
    "error": "Login failed: 403 Forbidden",
    "operator_notification_sent": true
  }'
);
```

## Processing States & State Diagram

### Report Status Enum Values

```
pending     - Initial state, report received but not yet processed
processing  - Actively being scraped/analyzed
completed   - Successfully processed through all stages
failed      - Processing failed permanently (max retries exceeded)
```

### Complete State Transition Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       REPORT LIFECYCLE                          │
└─────────────────────────────────────────────────────────────────┘

EMAIL RECEIVED
      │
      ├─→ INSERT INTO reports (status='pending')
      │
      ↓
[PENDING]  ← Initial state, waiting for processing
      │
      ├─ Scraper Service starts processing
      │
      ↓
[PROCESSING]  ← Scraper actively working
      │
      ├─ SUCCESS?
      │  │
      │  ├─ YES → raw_content populated
      │  │        report_images created
      │  │        status='processing' (for AI stage)
      │  │
      │  └─ NO → error_message set
      │         retry_count incremented
      │         Check if retry eligible:
      │         ├─ retry_count < 3? YES
      │         ├─ created_at > 24h ago? NO
      │         │  → status='failed'
      │         │    schedule retry with backoff
      │         │    log event with retry metadata
      │         │
      │         └─ YES (both conditions fail)
      │            → status='failed'
      │            → send manual review email
      │            → log CRITICAL event
      │
      ↓
[AI ANALYSIS STAGE]  ← Proceed to analysis if scraping succeeded
      │
      ├─ AI Analyzer Service processes
      │
      ├─ SUCCESS?
      │  │
      │  ├─ YES → analyses created
      │  │        sentiment, summary populated
      │  │        key_trades extracted
      │  │        status='completed'
      │  │        processed_at = NOW() [automatic trigger]
      │  │        log INFO event
      │  │
      │  └─ NO → error_message set
      │         retry_count incremented
      │         Check if retry eligible:
      │         ├─ retry_count < 5? YES
      │         ├─ created_at > 24h ago? NO
      │         │  → status='failed'
      │         │    schedule retry (exponential backoff)
      │         │    log event
      │         │
      │         └─ YES (both conditions fail)
      │            → status='failed'
      │            → send manual review email
      │            → log ERROR event
      │
      ↓
[COMPLETED]  ← Ready for notification
      │
      ├─ Notification Service sends analysis
      │  ├─ Email: status='pending' → 'sent'/'failed'
      │  └─ Telegram: status='pending' → 'sent'/'failed'
      │
      ├─ All notifications sent?
      │  └─ YES → Report truly complete
      │
      ↓
[ARCHIVED] (Optional, after 2 years)
      │
      └─ Move to archive storage if configured
        Maintain referential integrity
        Update status='archived'

┌──────────────────────────────────────────┐
│ TERMINAL STATES                          │
├──────────────────────────────────────────┤
│ COMPLETED - All stages succeeded         │
│ FAILED    - Max retries exceeded         │
│ ARCHIVED  - Retained per policy (2yrs)   │
└──────────────────────────────────────────┘
```

### Notification Status Enum Values

```
pending   - Created but not yet sent
sent      - Delivered successfully
failed    - Delivery failed permanently
retrying  - Retry in progress
```

### Notification State Transitions

```
[pending]  ← Initial state
    │
    ├─ Send attempt
    │
    ├─ SUCCESS?
    │  │
    │  ├─ YES → [sent] (terminal)
    │  │       sent_at = NOW()
    │  │       message_id populated
    │  │       log INFO event
    │  │
    │  └─ NO → Check retry eligibility
    │         │
    │         ├─ retry_count < max_retries?
    │         │  ├─ YES → [retrying] (temporary)
    │         │  │       retry_count++
    │         │  │       schedule retry with backoff
    │         │  │       log WARNING event
    │         │  │
    │         │  └─ NO → [failed] (terminal)
    │         │         log ERROR event
    │         │         operator may resend manually
    │
    ↓
[sent] or [failed] (terminal states)
```

## Audit Logging & Event Trail

### Logging Philosophy

- **Event-based, not action-based**: Single log entry per significant event, not per SQL transaction
- **Contextual metadata**: Include duration, retry count, resource usage in JSONB metadata
- **Distributed tracing**: correlation_id enables following report through all services
- **Queryable by service and severity**: Indexes on service_name and log_level for rapid filtering

### Key Business Events to Log

| Event | Service | Log Level | Metadata | Purpose |
|-------|---------|-----------|----------|---------|
| Report received | email_webhook | INFO | broker, account, email_from | Audit trail of ingestion |
| Scraping started | scraper_service | DEBUG | report_url, user_agent | Operational visibility |
| Scraping completed | scraper_service | INFO | duration_ms, content_length, images_found | Performance metrics |
| Scraping failed | scraper_service | WARNING | error_code, duration_ms, retry_count | Failure diagnosis |
| Scraping abandoned | scraper_service | ERROR | max_retries, total_duration, operator_notified | Manual review needed |
| Analysis started | ai_analyzer | DEBUG | model, tokens_estimated | Operational visibility |
| Analysis completed | ai_analyzer | INFO | tokens_used, api_cost, sentiment, processing_time_ms | Cost tracking & metrics |
| Analysis failed | ai_analyzer | WARNING | error, retry_count, tokens_used | Failure diagnosis |
| Analysis abandoned | ai_analyzer | ERROR | max_retries, total_cost, operator_notified | Manual review needed |
| Email sent | notification_service | INFO | channel, recipient, delivery_latency_ms | Delivery confirmation |
| Telegram sent | notification_service | INFO | channel, chat_id, message_id, latency_ms | Delivery confirmation |
| Notification failed | notification_service | WARNING | channel, error_code, retry_count | Failure diagnosis |

### Example Log Entries

**Scraping Completed Successfully:**
```sql
INSERT INTO system_logs (
  service_name, log_level, message, report_id, correlation_id, metadata
) VALUES (
  'scraper_service',
  'INFO',
  'Report scraping completed successfully',
  '550e8400-e29b-41d4-a716-446655440000',
  '12345678-1234-1234-1234-123456789012',
  '{
    "duration_ms": 3200,
    "login_duration_ms": 1200,
    "content_extraction_ms": 1800,
    "images_found": 2,
    "tradingview_links": 1,
    "content_length_bytes": 45823,
    "page_load_time_ms": 850
  }'
);
```

**AI Analysis Cost Tracking:**
```sql
INSERT INTO system_logs (
  service_name, log_level, message, report_id, correlation_id, metadata
) VALUES (
  'ai_analyzer',
  'INFO',
  'Report analysis completed',
  '550e8400-e29b-41d4-a716-446655440000',
  '12345678-1234-1234-1234-123456789012',
  '{
    "ai_provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "input_tokens": 847,
    "output_tokens": 400,
    "total_tokens": 1247,
    "api_cost": 0.0312,
    "processing_time_ms": 2150,
    "sentiment": "bullish",
    "confidence": 0.87,
    "key_trades_extracted": 8
  }'
);
```

**Failure Diagnosis:**
```sql
INSERT INTO system_logs (
  service_name, log_level, message, report_id, correlation_id, metadata, stack_trace
) VALUES (
  'scraper_service',
  'ERROR',
  'Login failed, max retries exceeded',
  '550e8400-e29b-41d4-a716-446655440000',
  '12345678-1234-1234-1234-123456789012',
  '{
    "retry_count": 3,
    "max_retries": 3,
    "total_duration_hours": 6.5,
    "last_error_code": 403,
    "last_error_message": "Forbidden",
    "portal_url": "https://broker.com/login",
    "operator_notification_sent": true
  }',
  'Traceback (most recent call last):...
  playwrightError: NavigationTimeout after 30000ms'
);
```

### Querying the Audit Trail

**Find all events for a specific report:**
```sql
SELECT service_name, log_level, message, created_at, metadata
FROM system_logs
WHERE report_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY created_at ASC;
```

**Trace a report across all services:**
```sql
SELECT
  created_at,
  service_name,
  log_level,
  message,
  metadata->>'duration_ms' as duration_ms,
  metadata->>'error_code' as error_code
FROM system_logs
WHERE correlation_id = '12345678-1234-1234-1234-123456789012'
ORDER BY created_at ASC;
```

**Find all failures in the last 24 hours:**
```sql
SELECT
  report_id,
  service_name,
  message,
  metadata->>'error_code' as error,
  created_at
FROM system_logs
WHERE log_level IN ('ERROR', 'WARNING')
  AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

**Calculate total cost of all analyses:**
```sql
SELECT
  SUM((metadata->>'api_cost')::DECIMAL) as total_cost,
  AVG((metadata->>'api_cost')::DECIMAL) as avg_cost,
  COUNT(*) as total_analyses
FROM system_logs
WHERE service_name = 'ai_analyzer'
  AND log_level = 'INFO'
  AND message = 'Report analysis completed'
  AND created_at > NOW() - INTERVAL '30 days';
```

### Log Retention & Cleanup

**Active logs:** Keep in system_logs table for 30 days
**Archived logs:** Move to system_logs_archive table (separate table) for historical queries
**Permanent retention:** Keep archived logs for 2 years per data retention policy

**Example maintenance procedure:**
```sql
-- Archive logs older than 30 days (run daily via cron)
INSERT INTO system_logs_archive
SELECT * FROM system_logs WHERE created_at < NOW() - INTERVAL '30 days';

-- Clean up archived logs older than 2 years
DELETE FROM system_logs_archive WHERE created_at < NOW() - INTERVAL '2 years';

-- Analyze table after bulk operations
ANALYZE system_logs;
```

## Integration Points

### Service: Email Webhook Receiver

**Responsibility:** Receives incoming emails, extracts metadata, creates initial report record

**Database Operations:**
```sql
-- Write: Create initial report
INSERT INTO reports (
  email_from,
  email_subject,
  email_message_id,  -- PRIMARY deduplication key
  email_received_at,
  report_url,        -- Extracted from email body
  status,
  metadata
) VALUES (...)
RETURNING id as report_id;

-- Write: Log ingestion event
INSERT INTO system_logs (...) VALUES (...);

-- Read: Check for duplicate (if implementing at application level)
SELECT id FROM reports WHERE email_message_id = ?;
```

**Error Handling:**
- Duplicate email_message_id → Do not create new record, return existing report_id
- Missing report_url → Reject email, log ERROR, alert operator
- Database connection failure → Retry with exponential backoff, fail webhook request

**Environment Variables Required:**
```
DATABASE_URL=postgresql://trading_user:password@localhost:5432/trading_reports
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10
CORRELATION_ID_HEADER=X-Correlation-ID
```

### Service: Scraper (Playwright)

**Responsibility:** Log into web portals, extract report content and images, update report status

**Database Operations:**
```sql
-- Read: Get pending/processing reports
SELECT id, report_url, metadata FROM reports
WHERE status IN ('pending', 'processing')
  AND retry_count < 3
  AND (last_retry_at IS NULL OR last_retry_at < NOW() - INTERVAL '1 hour')
ORDER BY created_at ASC
LIMIT 10;

-- Write: Update report status to processing
UPDATE reports SET status = 'processing' WHERE id = ?;

-- Write: Insert extracted images
INSERT INTO report_images (report_id, image_url, ...) VALUES (...);

-- Write: Update report with scraped content
UPDATE reports SET
  raw_content = ?,
  report_title = ?,
  status = 'processing',
  metadata = jsonb_set(metadata, '{scrape_duration_ms}', ?)
WHERE id = ?;

-- Write: Log scraping event
INSERT INTO system_logs (...) VALUES (...);

-- Write (on failure): Update status and error
UPDATE reports SET
  status = 'failed',
  error_message = ?,
  retry_count = retry_count + 1,
  last_retry_at = NOW()
WHERE id = ?;
```

**Query Pattern: Batch Processing**
```sql
-- Get next batch of reports to scrape (respecting retry schedule)
WITH backoff_calculated AS (
  SELECT
    id,
    retry_count,
    POWER(2, retry_count)::INTEGER * 60 as backoff_seconds,
    NOW() - INTERVAL '1 second' * POWER(2, retry_count)::INTEGER * 60 as next_eligible
  FROM reports
  WHERE status IN ('pending', 'processing')
    AND retry_count < 3
)
SELECT id, report_url, email_subject
FROM backoff_calculated
WHERE last_retry_at IS NULL OR last_retry_at < next_eligible
ORDER BY created_at ASC
LIMIT 10;
```

**Error Handling:**
- Login failure → Increment retry_count, schedule retry with backoff
- Timeout (>30s) → Mark as failed, alert operator
- Page not found (404) → Mark as permanently failed, log ERROR
- Database constraint violation → Rollback, log CRITICAL, alert developer

### Service: AI Analyzer (Anthropic/Groq)

**Responsibility:** Read report content, call AI API, parse results, create analysis record

**Database Operations:**
```sql
-- Read: Get processed reports without analyses
SELECT r.id, r.raw_content, r.report_title
FROM reports r
LEFT JOIN analyses a ON r.id = a.report_id
WHERE r.status = 'processing'
  AND a.id IS NULL
  AND r.retry_count < 5
ORDER BY r.created_at ASC
LIMIT 10;

-- Write: Create analysis record
INSERT INTO analyses (
  report_id,
  ai_provider,
  model_used,
  prompt_template,
  summary,
  key_trades,
  sentiment,
  confidence_score,
  tokens_used,
  api_cost,
  processing_time_ms
) VALUES (...)
RETURNING id as analysis_id;

-- Write: Mark report complete
UPDATE reports SET status = 'completed'
WHERE id = ?;
-- Automatic trigger sets processed_at = NOW()

-- Write: Log analysis event
INSERT INTO system_logs (...) VALUES (...);

-- Write (on failure): Update status
UPDATE reports SET
  status = 'failed',
  error_message = ?,
  retry_count = retry_count + 1,
  last_retry_at = NOW()
WHERE id = ?;
```

**API Cost Tracking:**
```sql
-- Calculate daily AI costs
SELECT
  DATE(created_at) as date,
  ai_provider,
  model_used,
  COUNT(*) as analyses_run,
  SUM(api_cost) as total_cost,
  AVG(processing_time_ms) as avg_duration_ms,
  SUM(tokens_used) as total_tokens
FROM analyses
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at), ai_provider, model_used
ORDER BY date DESC, ai_provider;
```

**Error Handling:**
- API timeout → Retry with exponential backoff (5 retries)
- Invalid API key → Fail immediately (no retry), alert operator, log CRITICAL
- Rate limiting → Retry with exponential backoff
- Malformed response → Log ERROR, mark report failed, require manual review

### Service: Notification Dispatcher

**Responsibility:** Send analysis summaries via email and Telegram, track delivery status

**Database Operations:**
```sql
-- Read: Get analyses needing notifications
SELECT a.id, r.id as report_id, a.summary, a.sentiment, a.key_trades
FROM analyses a
JOIN reports r ON a.report_id = r.id
LEFT JOIN notifications n ON a.id = n.analysis_id
WHERE NOT EXISTS (
  SELECT 1 FROM notifications
  WHERE analysis_id = a.id
    AND status = 'sent'
)
ORDER BY a.created_at ASC
LIMIT 20;

-- Write: Create notification records
INSERT INTO notifications (
  analysis_id,
  channel,
  recipient,
  status,
  message_content,
  metadata
) VALUES
  (?, 'email', 'trader@example.com', 'pending', ?, ?),
  (?, 'telegram', '123456789', 'pending', ?, ?);

-- Write: Update notification on successful send
UPDATE notifications SET
  status = 'sent',
  sent_at = NOW(),
  message_id = ?,
  metadata = jsonb_set(metadata, '{delivery_latency_ms}', ?)
WHERE id = ?;

-- Write (on failure): Update status with retry
UPDATE notifications SET
  status = 'retrying',
  retry_count = retry_count + 1,
  error_message = ?,
  metadata = jsonb_set(metadata, '{failed_attempt}', 'now()')
WHERE id = ?
  AND retry_count < max_retries;

-- Write: Log notification event
INSERT INTO system_logs (...) VALUES (...);
```

**Query Pattern: Retry Eligible Notifications**
```sql
-- Find notifications ready for retry (with exponential backoff)
SELECT n.* FROM notifications n
WHERE n.status = 'retrying'
  AND n.retry_count < n.max_retries
  AND n.updated_at < NOW() - INTERVAL '1 second' * POWER(2, n.retry_count)
ORDER BY n.created_at ASC
LIMIT 10;
```

**Error Handling:**
- Email delivery failure → Retry up to 3 times with backoff
- Telegram API error → Retry up to 3 times with backoff
- Invalid recipient → Mark as failed permanently, log ERROR
- Database transaction failure → Rollback, retry entire operation

### Service: N8N Orchestration

**Responsibility:** Trigger service webhooks based on report status changes

**Database Operations (Read-Only):**
```sql
-- Read: Monitor report status for workflow triggers
-- N8N polling query (runs every 5 minutes)
SELECT
  id,
  status,
  updated_at,
  metadata
FROM reports
WHERE status IN ('pending', 'processing', 'completed', 'failed')
  AND updated_at > NOW() - INTERVAL '5 minutes'
ORDER BY updated_at DESC;

-- N8N calls Python service webhooks based on status
-- Email Webhook Service: POST /webhook/email?report_id={id}
-- Scraper Service: POST /webhook/scrape?report_id={id}
-- AI Analyzer: POST /webhook/analyze?report_id={id}
-- Notification Service: POST /webhook/notify?report_id={id}
```

**Note:** N8N does NOT write directly to database. All writes are performed by Python services.

## Performance & Query Patterns

### Expected Query Patterns

**1. Chronological Report Listing**
```sql
-- List all reports from past 7 days
SELECT
  id, email_from, report_title, status, created_at
FROM reports
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 50;
-- Uses: idx_reports_created_at
```

**2. Active Report Monitoring**
```sql
-- Find reports currently being processed (stuck reports)
SELECT
  id, email_subject, status, retry_count,
  EXTRACT(EPOCH FROM (NOW() - created_at)) as age_seconds
FROM reports
WHERE status != 'completed'
  AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at ASC;
-- Uses: idx_reports_status (partial index for status != 'completed')
```

**3. Symbol/Broker Filtering**
```sql
-- Find all reports for specific broker
SELECT r.id, r.email_subject, r.created_at, a.sentiment
FROM reports r
LEFT JOIN analyses a ON r.id = a.report_id
WHERE r.metadata->>'broker' = 'XM'
  AND r.created_at > NOW() - INTERVAL '30 days'
ORDER BY r.created_at DESC;
-- Note: No index needed if metadata filtering is infrequent (JSONB scan acceptable)
-- If frequent, add: CREATE INDEX idx_reports_broker ON reports((metadata->>'broker'))
```

**4. Full-Text Search on Report Content**
```sql
-- Search for specific trading instrument mentions
SELECT
  r.id, r.email_subject, r.created_at,
  ts_rank_cd(to_tsvector('english', r.raw_content), to_tsquery('english', 'gold | xauusd')) as rank
FROM reports r
WHERE to_tsvector('english', r.raw_content) @@ to_tsquery('english', 'gold | xauusd')
ORDER BY rank DESC
LIMIT 20;
-- Uses: idx_reports_content_search (GIN index on to_tsvector)
```

**5. Sentiment Analysis Dashboard**
```sql
-- Sentiment distribution over time
SELECT
  DATE(a.created_at) as date,
  a.sentiment,
  COUNT(*) as count,
  AVG(a.confidence_score) as avg_confidence
FROM analyses a
WHERE a.created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(a.created_at), a.sentiment
ORDER BY date DESC, a.sentiment;
-- Uses: idx_analyses_created_at, idx_analyses_sentiment
```

**6. Notification Delivery Status**
```sql
-- Check notification success rate by channel
SELECT
  channel,
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE status = 'sent') as sent,
  COUNT(*) FILTER (WHERE status = 'failed') as failed,
  COUNT(*) FILTER (WHERE status = 'retrying') as retrying,
  ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'sent') / COUNT(*), 2) as success_rate
FROM notifications
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY channel;
-- Uses: idx_notifications_channel, idx_notifications_status
-- Or faster: Use vw_notification_stats view (pre-aggregated)
```

**7. Processing Time Analysis**
```sql
-- Identify reports with unusual processing times
SELECT
  r.id,
  r.email_subject,
  EXTRACT(EPOCH FROM (r.processed_at - r.created_at)) as processing_time_seconds,
  r.status
FROM reports r
WHERE r.processed_at IS NOT NULL
  AND EXTRACT(EPOCH FROM (r.processed_at - r.created_at)) >
      (SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (processed_at - created_at)))
       FROM reports WHERE processed_at IS NOT NULL)
ORDER BY processing_time_seconds DESC
LIMIT 20;
-- Uses: idx_reports_created_at (for date filtering if added)
```

**8. Reports Needing Images**
```sql
-- Find reports with specific image types
SELECT
  r.id, r.email_subject, COUNT(ri.id) as image_count
FROM reports r
LEFT JOIN report_images ri ON r.id = ri.report_id
WHERE ri.image_type IN ('chart', 'tradingview_link')
GROUP BY r.id
HAVING COUNT(ri.id) > 0
ORDER BY r.created_at DESC;
-- Uses: idx_images_report_id
```

### Query Optimization Recommendations

**1. Use Partial Indexes**
Already implemented in schema for status != 'completed' filters.

**2. Consider Materialized Views for Heavy Aggregations**
```sql
-- If vw_daily_metrics is queried frequently (hourly dashboards)
CREATE MATERIALIZED VIEW mv_daily_metrics_cached AS
SELECT * FROM vw_daily_metrics;

-- Refresh periodically (hourly or daily)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_metrics_cached;

-- Query the materialized view instead
SELECT * FROM mv_daily_metrics_cached WHERE date > NOW()::DATE - 7;
```

**3. Connection Pooling**
Use PgBouncer or application-level pooling (via sqlalchemy.pool) to reuse connections.

**4. Prepared Statements**
Use parameterized queries to benefit from query plan caching.

**5. Batch Operations**
Insert/update reports in batches (10-100 per transaction) for throughput.

**6. Table Partitioning (Future)**
If system grows to millions of reports:
```sql
-- Partition reports by creation date (e.g., monthly)
CREATE TABLE reports_2025_11 PARTITION OF reports
FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

### Index Strategy Summary

**Current indexes cover:**
- ✓ Primary key lookups (id)
- ✓ Chronological queries (created_at DESC)
- ✓ Status filtering (status, partial)
- ✓ Foreign key joins (report_id, analysis_id)
- ✓ Full-text search (GIN on to_tsvector)
- ✓ Image deduplication (image_hash)

**Potential additions if performance issues arise:**
- Consider compound index on `(status, created_at DESC)` for filtering + sorting
- Add index on `metadata->>'broker'` if broker filtering becomes frequent
- Add index on `metadata->>'symbol'` if symbol search is common

## Security & Credentials

### Environment Variables Required

All services must be configured with these environment variables (never hardcode or commit):

```bash
# Database connection
DATABASE_URL=postgresql://trading_user:${DATABASE_PASSWORD}@${DATABASE_HOST}:5432/trading_reports
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10
DATABASE_SSL_MODE=require  # 'require' or 'verify-full' in production

# Service configuration
CORRELATION_ID_HEADER=X-Correlation-ID
LOG_LEVEL=INFO
SERVICE_NAME=scraper_service  # Changes per service

# AI provider credentials (never in database)
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk-...

# Email configuration
EMAIL_PROVIDER_PASSWORD=app-specific-password  # Not user password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# Telegram configuration
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# Optional: Credentials vault
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=hvs.CAESIxxxxxxx
```

### Database User Permissions

**Create application user with minimal privileges:**
```sql
-- Create database user for application
CREATE USER trading_user WITH PASSWORD 'complex_random_password';

-- Grant only necessary privileges
GRANT CONNECT ON DATABASE trading_reports TO trading_user;
GRANT USAGE ON SCHEMA public TO trading_user;

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE ON reports TO trading_user;
GRANT SELECT, INSERT, UPDATE ON analyses TO trading_user;
GRANT SELECT, INSERT, UPDATE ON notifications TO trading_user;
GRANT SELECT, INSERT, UPDATE ON report_images TO trading_user;
GRANT SELECT, INSERT ON system_logs TO trading_user;

-- Grant sequence permissions (for auto-increment if used)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO trading_user;

-- Grant function execution (for triggers)
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO trading_user;

-- Revoke dangerous permissions
REVOKE CREATE ON SCHEMA public FROM trading_user;
REVOKE DROP ON SCHEMA public FROM trading_user;
```

**Read-only analytics user (optional):**
```sql
CREATE USER analytics_user WITH PASSWORD 'complex_password';
GRANT CONNECT ON DATABASE trading_reports TO analytics_user;
GRANT USAGE ON SCHEMA public TO analytics_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;
GRANT SELECT ON ALL VIEWS IN SCHEMA public TO analytics_user;
-- No INSERT, UPDATE, DELETE permissions
```

### PostgreSQL SSL/TLS Configuration

**Server-side (database host):**
```postgresql
# In postgresql.conf
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
ssl_ca_file = '/path/to/ca.crt'  # Optional, for client cert verification

# In pg_hba.conf - Require SSL for remote connections
hostssl all trading_user 0.0.0.0/0 md5  # Or scram-sha-256
```

**Client-side (application):**
```python
# Using psycopg2 / sqlalchemy
DATABASE_URL = "postgresql://trading_user:password@host:5432/trading_reports?sslmode=require"

# Connection parameters
conn = psycopg2.connect(
    dbname="trading_reports",
    user="trading_user",
    password=os.getenv('DATABASE_PASSWORD'),
    host=os.getenv('DATABASE_HOST'),
    port=5432,
    sslmode='require',  # Enforce SSL
    connect_timeout=10
)
```

### Data at Rest: Sensitive Information Policy

**NEVER store in database:**
- Email account passwords → Use environment variables + secrets vault
- API keys (Anthropic, Groq) → Use environment variables + secrets vault
- Telegram bot tokens → Use environment variables + secrets vault
- Trading account passwords → Use environment variables or external credential manager

**Acceptable to store:**
- Email addresses (recipient contact info) - not sensitive
- Report URLs (public web pages)
- Image URLs (public web pages)
- AI analysis results (derived data, no credentials)
- System logs (operational data)

**Application-level encryption (if needed for future compliance):**
```python
# Example: Encrypt sensitive metadata before storing
from cryptography.fernet import Fernet

cipher = Fernet(os.getenv('ENCRYPTION_KEY'))
encrypted_data = cipher.encrypt(sensitive_string.encode())

# Store encrypted_data in metadata JSONB as base64
metadata = {
    'encrypted_account_number': encrypted_data.decode()
}
```

## Implementation Details

### PostgreSQL Version & Setup

**Requirements:**
- PostgreSQL 15 or newer (tested on 16.1)
- Required extensions: uuid-ossp, pg_trgm
- Disk space: ~1GB per 100,000 reports (with 50KB average content)

**Initialization Steps:**

1. **Create database and user:**
```sql
-- Connect as superuser (postgres)
CREATE DATABASE trading_reports;
CREATE USER trading_user WITH PASSWORD 'strong_random_password';
GRANT CONNECT ON DATABASE trading_reports TO trading_user;
```

2. **Apply schema:**
```bash
# Using psql
psql -U postgres trading_reports < database_schema.sql

# Or from Python application
import psycopg2
conn = psycopg2.connect("dbname=postgres user=postgres")
with open('database_schema.sql', 'r') as f:
    conn.cursor().execute(f.read())
conn.commit()
```

3. **Verify installation:**
```sql
-- Connect as trading_user
\d reports  -- Should show reports table structure
\d+ vw_reports_with_analysis  -- Should show view
SELECT version();  -- Verify PostgreSQL version
```

### Custom ENUM Types

The schema defines four ENUM types for type safety:

```sql
-- Report processing status
CREATE TYPE report_status AS ENUM ('pending', 'processing', 'completed', 'failed');

-- Notification delivery channels
CREATE TYPE notification_channel AS ENUM ('telegram', 'email');

-- Notification delivery status
CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'failed', 'retrying');

-- AI provider selection
CREATE TYPE ai_provider AS ENUM ('anthropic', 'groq');

-- Sentiment classification
CREATE TYPE sentiment AS ENUM ('bullish', 'bearish', 'neutral', 'mixed');
```

**Advantage:** Type safety at database level prevents invalid values.
**Updating ENUMs:** Requires careful schema migration (cannot remove values).

### Triggers & Functions

**Function 1: update_updated_at_column()**
```sql
-- Automatically sets updated_at to NOW() on UPDATE
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Applied to: reports, notifications tables
```

**Function 2: set_processed_at()**
```sql
-- Automatically sets processed_at when status becomes 'completed'
CREATE OR REPLACE FUNCTION set_processed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        NEW.processed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Applied to: reports table
```

### Views for Common Queries

**View 1: vw_reports_with_analysis**
Joins reports with their latest analysis and counts for dashboards.
```sql
SELECT
  r.id,
  r.email_received_at,
  r.email_subject,
  r.report_url,
  r.status,
  r.created_at,
  r.processed_at,
  a.id as analysis_id,
  a.ai_provider,
  a.summary,
  a.sentiment,
  a.confidence_score,
  a.key_trades,
  COUNT(ri.id) as image_count,
  COUNT(n.id) as notification_count,
  COUNT(n.id) FILTER (WHERE n.status = 'sent') as notifications_sent
FROM reports r
LEFT JOIN analyses a ON r.id = a.report_id
LEFT JOIN report_images ri ON r.id = ri.report_id
LEFT JOIN notifications n ON a.id = n.analysis_id
GROUP BY r.id, a.id;
```

**View 2: vw_notification_stats**
Aggregates notification delivery statistics by channel and status.
```sql
SELECT
  channel,
  status,
  COUNT(*) as count,
  AVG(retry_count) as avg_retries,
  MAX(created_at) as last_notification
FROM notifications
GROUP BY channel, status;
```

**View 3: vw_daily_metrics**
Daily processing metrics for monitoring and optimization.
```sql
SELECT
  DATE(created_at) as date,
  COUNT(*) as total_reports,
  COUNT(*) FILTER (WHERE status = 'completed') as completed,
  COUNT(*) FILTER (WHERE status = 'failed') as failed,
  AVG(EXTRACT(EPOCH FROM (processed_at - created_at))) as avg_processing_time_seconds
FROM reports
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### Data Types & Constraints

**UUID vs Integer IDs:**
- Used UUID for all primary keys (uuid_generate_v4())
- Advantage: Distributed system ready, no sequence coordination needed
- Disadvantage: Larger storage (16 bytes vs 4-8 bytes)
- Acceptable tradeoff for modest scale (< 10M records)

**JSONB for Flexible Metadata:**
- metadata columns allow schema evolution without migrations
- Can store arbitrary key-value pairs per record
- Supports indexes via GIN for querying

**CHECK Constraints:**
```sql
-- URL validation
CONSTRAINT valid_url CHECK (report_url ~* '^https?://')

-- Confidence score bounds
CONSTRAINT valid_confidence CHECK (confidence_score BETWEEN 0 AND 1)

-- Percentage bounds
CONSTRAINT valid_win_rate CHECK (win_rate BETWEEN 0 AND 100)

-- Non-negative counts
CONSTRAINT valid_retry CHECK (retry_count >= 0)
CONSTRAINT valid_tokens CHECK (tokens_used > 0)
```

**Referential Integrity:**
- ON DELETE CASCADE: report deletion removes related images, analyses, notifications
- ON DELETE SET NULL: system_logs references to deleted reports become NULL

### Example: Initialization Script

```python
#!/usr/bin/env python3
"""Initialize trading_reports database schema."""

import psycopg2
import os
from pathlib import Path

def init_database():
    """Apply schema to database."""

    # Read schema file
    schema_path = Path(__file__).parent / "database_schema.sql"
    with open(schema_path) as f:
        schema_sql = f.read()

    # Connect as superuser
    conn = psycopg2.connect(
        dbname=os.getenv('POSTGRES_DB', 'postgres'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432)
    )

    try:
        cursor = conn.cursor()

        # Create database if not exists
        cursor.execute("CREATE DATABASE trading_reports;")
        conn.commit()
        print("✓ Database created")

        # Close and reconnect to new database
        conn.close()

        conn = psycopg2.connect(
            dbname='trading_reports',
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD'),
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', 5432)
        )

        # Apply schema
        cursor = conn.cursor()
        cursor.execute(schema_sql)
        conn.commit()
        print("✓ Schema applied")

        # Verify tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"✓ Tables created: {', '.join(tables)}")

    finally:
        conn.close()

if __name__ == '__main__':
    init_database()
```

## Testing & Validation

### Schema Verification Queries

**1. Verify all tables exist:**
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
-- Should return: analyses, notifications, report_images, reports, system_logs
```

**2. Verify indexes:**
```sql
SELECT indexname FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY indexname;
-- Should include: idx_reports_created_at, idx_analyses_report_id, etc.
```

**3. Verify views:**
```sql
SELECT viewname FROM pg_views
WHERE schemaname = 'public'
ORDER BY viewname;
-- Should return: vw_daily_metrics, vw_notification_stats, vw_reports_with_analysis
```

**4. Verify triggers:**
```sql
SELECT trigger_name, event_object_table
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table;
-- Should include: set_report_processed_at, update_reports_updated_at, etc.
```

**5. Verify custom types:**
```sql
SELECT typname FROM pg_type
WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
ORDER BY typname;
-- Should include: ai_provider, notification_channel, notification_status, report_status, sentiment
```

### Sample Data for Testing

**Insert test report:**
```sql
INSERT INTO reports (
  email_from,
  email_subject,
  email_message_id,
  email_received_at,
  report_url,
  status,
  metadata
) VALUES (
  'test@example.com',
  'Test Trading Report',
  '<test-message-id@example.com>',
  NOW(),
  'https://example.com/report/test',
  'pending',
  '{"broker": "TEST", "test": true}'
)
RETURNING id;
```

**Insert test image:**
```sql
INSERT INTO report_images (
  report_id,
  image_url,
  image_type,
  mime_type,
  width,
  height,
  sequence_order
) VALUES (
  '[report_id]',
  'https://example.com/test-chart.png',
  'chart',
  'image/png',
  800,
  600,
  0
);
```

**Insert test analysis:**
```sql
INSERT INTO analyses (
  report_id,
  ai_provider,
  model_used,
  summary,
  sentiment,
  confidence_score,
  tokens_used,
  api_cost,
  processing_time_ms
) VALUES (
  '[report_id]',
  'anthropic',
  'claude-3-5-sonnet-20241022',
  'This is a test analysis',
  'neutral',
  0.65,
  123,
  0.0045,
  1200
);
```

**Create test notifications:**
```sql
INSERT INTO notifications (
  analysis_id,
  channel,
  recipient,
  status
) VALUES
  ('[analysis_id]', 'email', 'test@example.com', 'pending'),
  ('[analysis_id]', 'telegram', '123456789', 'pending');
```

**Verify via view:**
```sql
SELECT * FROM vw_reports_with_analysis;
-- Should show test report with analysis and notification counts
```

### Testing State Transitions

**Test: Report transitions from pending to completed**
```sql
-- Start with pending report
SELECT id, status, created_at, processed_at
FROM reports WHERE email_message_id = '<test-message-id@example.com>';
-- Result: status='pending', processed_at=NULL

-- Update status to processing
UPDATE reports
SET status = 'processing'
WHERE email_message_id = '<test-message-id@example.com>';

-- Update status to completed
UPDATE reports
SET status = 'completed'
WHERE email_message_id = '<test-message-id@example.com>';

-- Verify trigger set processed_at automatically
SELECT id, status, created_at, processed_at
FROM reports WHERE email_message_id = '<test-message-id@example.com>';
-- Result: status='completed', processed_at=NOW() (via trigger)
```

**Test: Retry logic with retry_count**
```sql
-- Simulate first scraping attempt failure
UPDATE reports
SET status = 'failed',
    error_message = 'Login timeout',
    retry_count = 1,
    last_retry_at = NOW()
WHERE id = '[report_id]';

-- Application checks retry eligibility
-- (retry_count < 3 AND created_at > 24h ago AND last_retry_at + backoff <= NOW())
-- If eligible, schedule retry

-- Simulate second failure
UPDATE reports
SET status = 'failed',
    error_message = 'Login timeout (retry 2)',
    retry_count = 2,
    last_retry_at = NOW()
WHERE id = '[report_id]';

-- Simulate third failure (max retries)
UPDATE reports
SET status = 'failed',
    error_message = 'Max retries exceeded after 3 attempts',
    retry_count = 3,
    last_retry_at = NOW()
WHERE id = '[report_id]';

-- Operator notified manually
```

### Testing Full Data Flow

**Scenario: Complete report from email to notification**
```sql
-- 1. Email webhook creates report
INSERT INTO reports (...) VALUES (...);
-- Verify: SELECT * FROM reports ORDER BY created_at DESC LIMIT 1;

-- 2. Scraper updates content
UPDATE reports SET status = 'processing', raw_content = '...', ...
WHERE id = '[id]';
-- Verify: SELECT id, status, content_length FROM reports WHERE id = '[id]';

-- 3. Add images
INSERT INTO report_images (...) VALUES (...);
-- Verify: SELECT COUNT(*) FROM report_images WHERE report_id = '[id]';

-- 4. AI creates analysis
INSERT INTO analyses (...) VALUES (...);
-- Verify: SELECT * FROM analyses WHERE report_id = '[id]';

-- 5. Update report to completed
UPDATE reports SET status = 'completed' WHERE id = '[id]';
-- Verify trigger: SELECT processed_at FROM reports WHERE id = '[id]';

-- 6. Create notifications
INSERT INTO notifications (...) VALUES (...);
-- Verify: SELECT COUNT(*) FROM notifications WHERE status = 'pending';

-- 7. Mark sent
UPDATE notifications SET status = 'sent', sent_at = NOW() ...;
-- Verify: SELECT COUNT(*) FROM notifications WHERE status = 'sent';

-- 8. View aggregated result
SELECT * FROM vw_reports_with_analysis WHERE id = '[id]';
-- Should show: 1 report, 1 analysis, 2 images, 2 notifications sent
```

## Dependencies & Roadmap Integration

### Phase 1 MVP Dependencies

**Phase 1 Sequence:**
1. **PostgreSQL Schema & Data Persistence (THIS SPEC)** - Foundation
2. Email Webhook Service - Depends on reports table
3. Scraper Service - Depends on reports table, writes to report_images
4. AI Analyzer Service - Depends on reports table, creates analyses records
5. Notification Service - Depends on analyses table, manages notifications
6. N8N Workflows - Orchestrates via webhooks (read-only database access)

### Services That Depend on This Schema

| Service | Reads | Writes | Frequency |
|---------|-------|--------|-----------|
| Email Webhook | Nothing | reports | Per email (10-50/day) |
| Scraper Service | reports | reports, report_images | Per report (10-50/day) |
| AI Analyzer | reports | analyses | Per report (10-50/day) |
| Notification Service | analyses | notifications | Per analysis (10-50/day) |
| N8N Workflow | reports | Nothing (webhook only) | Every 5 minutes |
| Dashboard/Monitoring | All tables | system_logs | Continuous |

### Future Phases Compatibility

**Phase 2: Multi-User Support**
- Add user_id column to reports, analyses (already in system_logs)
- Add user preferences table for notification settings per user
- Create row-level security policies for user isolation
- Schema can be extended without breaking current Phase 1

**Phase 3: Advanced Analytics**
- Add historical_analyses table for version tracking (optional)
- Create analysis_metrics table for aggregated statistics
- Use materialized views for expensive aggregations
- Consider data warehouse integration for OLAP queries

**Phase 4: Horizontal Scaling**
- Current schema works with read replicas
- Partition reports by date for improved query performance
- Consider separate analytics database with daily snapshots
- Archive old reports to cold storage (S3) with foreign key integrity

## Future Considerations

### Current Limitations & Scalability

**Current Design Assumptions:**
- Single user (no multi-tenancy)
- Single Python process updating database (N8N does not write)
- ~10-50 reports per day (modest volume)
- Reports kept indefinitely (2-year archive policy)
- No requirement for high-frequency queries (dashboards update every 5-10 minutes)

**Scaling Considerations (if volume increases 10x):**

1. **Connection Pooling:** Implement PgBouncer for 100+ connection limit
2. **Partitioning:** Partition reports by month once table exceeds 10M rows
3. **Read Replicas:** Use read-only replica for dashboard/monitoring queries
4. **Caching:** Add Redis for frequently accessed analysis summaries
5. **Archival:** Implement automatic archival of 2-year-old reports to separate schema

### Enhancement Ideas

**1. Content Versioning**
Currently, reports have one analysis per report (not versioned). If re-analysis is needed:
```sql
-- Option A: Add version column
ALTER TABLE analyses ADD COLUMN version INTEGER DEFAULT 1;
-- Option B: Keep analyses immutable, create new analysis with newer created_at
```

**2. Advanced Search**
Currently using PostgreSQL full-text search. For large-scale search:
```sql
-- Could integrate with Elasticsearch
-- Keep PostgreSQL as primary, sync to Elasticsearch for advanced search
-- Query: POST /api/search?q=gold&sentiment=bullish
```

**3. Cost Analytics Dashboard**
Track AI provider costs over time:
```sql
CREATE MATERIALIZED VIEW mv_monthly_costs AS
SELECT
  DATE_TRUNC('month', a.created_at) as month,
  a.ai_provider,
  COUNT(*) as analyses_run,
  SUM(a.api_cost) as total_cost,
  AVG(a.api_cost) as avg_cost,
  MIN(a.api_cost) as min_cost,
  MAX(a.api_cost) as max_cost
FROM analyses a
GROUP BY DATE_TRUNC('month', a.created_at), a.ai_provider;
```

**4. Smart Deduplication**
Current deduplication via email_message_id. Could enhance:
```sql
-- Calculate content hash for similar reports
CREATE OR REPLACE FUNCTION calculate_content_hash(content TEXT)
RETURNS TEXT AS $$
  SELECT md5(LOWER(REGEXP_REPLACE(content, '[^a-z0-9]+', '', 'g')))
$$ LANGUAGE sql IMMUTABLE;

-- Use to find similar reports
SELECT r1.id, r2.id,
  SIMILARITY(r1.raw_content, r2.raw_content) as similarity
FROM reports r1
JOIN reports r2 ON r1.id < r2.id
WHERE SIMILARITY(r1.raw_content, r2.raw_content) > 0.85
  AND r1.created_at > NOW() - INTERVAL '7 days';
-- Requires pg_trgm extension (already enabled)
```

**5. Audit Trail Compression**
For long-term storage, compress old logs:
```sql
-- Create summary log entries for old events
INSERT INTO system_logs_compressed
SELECT
  DATE(created_at),
  service_name,
  log_level,
  COUNT(*) as event_count,
  COUNT(*) FILTER (WHERE metadata->>'error_code' IS NOT NULL) as error_count
FROM system_logs
WHERE created_at < NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), service_name, log_level;

-- Delete original logs after compression
DELETE FROM system_logs WHERE created_at < NOW() - INTERVAL '30 days';
```

### Known Limitations & Workarounds

**1. JSONB Querying Performance**
Querying JSONB metadata without indexes is O(n). Workaround: Create specific indexes for frequently queried keys:
```sql
CREATE INDEX idx_reports_broker ON reports ((metadata->>'broker'));
```

**2. Trigger Performance**
Automatic timestamp updates add small overhead to every UPDATE. For high-write scenarios, consider:
```sql
-- Disable triggers temporarily for bulk updates
ALTER TABLE reports DISABLE TRIGGER update_reports_updated_at;
-- ... bulk update ...
ALTER TABLE reports ENABLE TRIGGER update_reports_updated_at;
ANALYZE reports;
```

**3. UUID Size**
UUIDs are 16 bytes vs 4 bytes for integers. For 1M records, that's ~12MB extra per table. Acceptable for current scale.

### Maintenance Tasks

**Daily (automated via cron):**
```bash
# Vacuum and analyze
*/6 * * * * psql trading_reports -c "VACUUM ANALYZE;"

# Monitor slow queries (if enabled)
0 * * * * psql trading_reports -c "SELECT query, calls, total_time FROM pg_stat_statements WHERE query NOT LIKE '%pg_stat_statements%' ORDER BY total_time DESC LIMIT 10;"
```

**Weekly (manual review):**
```sql
-- Check for stuck reports (status = processing for > 24 hours)
SELECT id, email_subject, status, created_at
FROM reports
WHERE status = 'processing'
  AND created_at < NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

-- Check for notifications stuck in 'retrying'
SELECT COUNT(*) FROM notifications
WHERE status = 'retrying'
  AND updated_at < NOW() - INTERVAL '24 hours';
```

**Monthly:**
```sql
-- Archive completed reports (if configured)
UPDATE reports SET status = 'archived'
WHERE status = 'completed'
  AND processed_at < NOW() - INTERVAL '2 years';

-- Archive old logs
INSERT INTO system_logs_archive
SELECT * FROM system_logs WHERE created_at < NOW() - INTERVAL '30 days';

DELETE FROM system_logs WHERE created_at < NOW() - INTERVAL '30 days';

-- Reindex for fragmentation
REINDEX TABLE reports;
REINDEX TABLE analyses;
```

## SQL Schema Reference

The complete, production-ready PostgreSQL schema is provided in:
`/Users/edmundo.figueroaherbas@medirect.com.mt/projects/personal/trading-report/agent-os/specs/2025-11-25-postgresql-schema-data-persistence/planning/database_schema.sql`

This schema file includes:
- All table definitions with constraints
- Complete index definitions
- Trigger and function definitions
- View definitions
- Permission grants for trading_user role
- Comments and documentation

**To initialize the database:**
```bash
psql -U postgres -d trading_reports -f database_schema.sql
```

**To verify successful initialization:**
```bash
psql -U trading_user -d trading_reports -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
# Should return: 5 (reports, report_images, analyses, notifications, system_logs)
```

## Summary

This PostgreSQL schema provides the complete data persistence layer for the trading report automation system. It features:

- **Robust state management** with clear status transitions and retry logic
- **Comprehensive audit logging** via event-based system_logs table
- **Efficient querying** with strategic indexes and pre-built views
- **Data integrity** via foreign keys, constraints, and triggers
- **Flexibility** via JSONB metadata for schema evolution
- **Security** through environment variable credential management and SSL/TLS
- **Single-user simplicity** with clear architecture for future multi-user support

The schema is immediately deployable and supports all Phase 1 services: Email Webhook, Scraper, AI Analyzer, and Notification services.
