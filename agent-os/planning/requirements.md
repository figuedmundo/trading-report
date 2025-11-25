# Spec Requirements: PostgreSQL Schema & Data Persistence

## Initial Description
User is building an automated trading report monitoring and analysis system. The system needs to:
- Monitor incoming emails for trading reports
- Extract URLs from emails
- Log into web portals automatically
- Scrape report content (including TradingView images)
- Analyze content using AI
- Send summarized reports via Email and Telegram
- Store all data in PostgreSQL database in a homelab environment

## Requirements Discussion

### First Round Questions

**Q1: Core Report Entity Structure**
Should we store: extracted text, source URL, and TradingView chart captures?

**Answer:** Yes - Store extracted text, source URL, and chart captures. For images, store links instead of files (no need for large file storage).

**Q2: Report Content Storage Strategy**
For large HTML/text (5-10MB per report with images), should we store inline in PostgreSQL with compression, or store as files on disk with database references?

**Answer:** Store links to images instead of files. Don't need large file storage.

**Q3: Analysis & Signals Relationship**
One report will have 1 AI analysis over time?

**Answer:** Correct - one report will have one AI analysis over time.

**Q4: Processing Status & Workflow States**
What states should reports go through? Should we track error states and retry queue?

**Answer:** User likes the workflow states (received → detected → scraped → analyzed → notified → archived). Wants suggestions on error states and retry queue.

**Q5: Audit & Access Logging**
What events need logging? Do we need to track per-portal login attempts separately?

**Answer:** Wants suggestions.

**Q6: Report Deduplication & Versioning**
How to detect duplicates? How to handle re-analyzed reports? How long keep old versions?

**Answer:** Wants suggestions.

**Q7: Credential Storage & Portal Configuration**
Should credentials be per-report override, in separate reusable table, or both? Should portal configuration live in database or config files?

**Answer:** Wants suggestions.

**Q8: Query Performance & Indexing**
For 100+ reports/month, which fields need indexes? Full-text search on content, or basic filtering?

**Answer:** Wants suggestions.

**Q9: Data Retention & Archival**
How long keep raw HTML vs summaries? Archive after 2 years? Move archived data to separate table/database?

**Answer:** Home project, wants suggestions (no regulatory compliance needed).

**Q10: N8N Integration**
Should N8N trigger workflows (Python services write data), or write directly to DB too? Webhook callbacks needed?

**Answer:** Wants suggestions.

**Q11: Multi-User Considerations**
Future-proofing for multi-user?

**Answer:** Single user always - no multi-user complexity needed.

**Q12: Encryption & Sensitive Data**
Encrypt at-rest sensitive fields (credentials, API keys) in database, or use environment variables?

**Answer:** Wants suggestions.

### Existing Code to Reference

**Code & Resources Found:**
- Playwright Scraper Implementation: `/Users/edmundo.figueroaherbas@medirect.com.mt/projects/personal/trading-report/refs/scraper.py`
  - Async Playwright setup with browser automation
  - Login handling pattern with credentials
  - Content extraction (HTML + text + images)
  - Image URL extraction from HTML

- FastAPI Scraper Service: `/Users/edmundo.figueroaherbas@medirect.com.mt/projects/personal/trading-report/refs/playwright_scraper_app.py`
  - FastAPI service architecture
  - API key authentication pattern
  - Browser manager lifecycle management
  - Structured logging (structlog)
  - Health check endpoints

- Database Schema Draft: `/Users/edmundo.figueroaherbas@medirect.com.mt/projects/personal/trading-report/agent-os/specs/2025-11-25-postgresql-schema-data-persistence/planning/database_schema.sql`
  - Complete PostgreSQL schema with UUIDs
  - Tables: reports, report_images, analyses, notifications, system_logs
  - Comprehensive indexes for performance
  - Views for analytics and reporting
  - Triggers for automatic timestamps

### Follow-up Questions

**Follow-up 1: Your "Working Ideas" - Where are they?**
You mentioned having "some working ideas" for database models, ERD diagrams, or credential management. Where can I find these?
- Are they in a specific file or directory?
- Should we reference them when building the spec?
- Do you have existing credential management patterns we should follow?

**Follow-up 2: Chart Image Handling Details**
For TradingView chart captures - should we:
- Store URLs only (if TradingView charts are publicly accessible)
- Store as file references if we download them
- Store base64 encoded or embedded iframe URLs for portals
- Store metadata about the chart (size, type, description)

**Follow-up 3: Retry Logic Parameters**
For error states and retry queues, we need:
- How many retry attempts before giving up? (suggest: 3 attempts for most operations, 5 for critical ones)
- What's the maximum time to keep retrying? (suggest: 24 hours, then mark as permanently failed)
- Should failed reports go to a manual review queue or just be archived?
- Different retry strategies for login failures vs. scraping failures vs. AI API failures?

**Follow-up 4: Audit Logging Detail Level**
For audit logging, what's your preference:
- Detailed timestamped action logs: "user accessed report X at time Y with result Z"
- Event-only logs: "report analysis started, completed, failed"
- Just success/failure counts?
- Do you want to track every login attempt to portals, or just failures?

**Follow-up 5: Deduplication Strategy**
For detecting duplicate reports:
- By email message ID + sender? (most reliable)
- By content hash? (catches forwarded reports with same content)
- By timestamp + sender within a time window? (catches same portal report accessed twice)
- Suggestions: Use email message ID as primary key for deduplication, store content hash as secondary check.

## Visual Assets

No visual assets provided.

## Requirements Summary

### Functional Requirements
- Capture incoming emails with trading report indicators
- Extract URLs from email content
- Store report metadata (sender, subject, email ID, received time)
- Securely store and use credentials for portal login
- Automate browser login and navigation to portal URLs
- Extract report content: text, HTML, images (as links)
- Store raw and processed report data in PostgreSQL
- Generate AI analysis/summaries for each report
- Track processing workflow states through defined pipeline
- Send notifications via email and Telegram
- Log all significant events and errors for auditing
- Support report archival after processing

### Processing Workflow States
- **received**: Email arrived, basic parsing done
- **detected**: Report pattern matched, URL extracted
- **scraped**: Browser login + content extraction complete
- **analyzed**: AI analysis generated
- **notified**: Notifications sent to user
- **archived**: Report moved to archive (2+ years old)

**Error States** (suggested):
- **scrape_failed**: Portal login or content extraction failed
- **analysis_failed**: AI API failed or timed out
- **notification_failed**: Email/Telegram delivery failed

### Reusability Opportunities
- **Playwright Integration**: Already have working scraper patterns in `/refs/scraper.py` - reuse the WebScraper class pattern
- **FastAPI Service**: Already have service architecture in `/refs/playwright_scraper_app.py` - follow same patterns for main API
- **Database Schema**: Reference the draft schema in `/agent-os/specs/2025-11-25-postgresql-schema-data-persistence/planning/database_schema.sql` - it already includes reports, analyses, notifications tables
- **Authentication Pattern**: Follow API key authentication from FastAPI app for webhook security
- **Structured Logging**: Use structlog pattern from FastAPI app for audit trails

### Scope Boundaries

**In Scope:**
- Email webhook endpoint to receive incoming emails
- Email parsing to extract URLs and metadata
- Credential storage (encrypted) for portal logins
- Playwright-based browser automation and login handling
- Content extraction (text, HTML, image links)
- PostgreSQL persistence with audit trails
- AI analysis integration (Groq/Anthropic API calls)
- Email and Telegram notification delivery
- Error handling and retry logic
- Report status tracking through workflow

**Out of Scope:**
- Multi-user support or access control
- Real-time dashboard or UI (Phase 2+)
- Advanced ML/trend analysis (Phase 3+)
- Trading platform integrations (Phase 4+)
- OAuth credential handling (Phase 5+)

### Technical Considerations

**Database Architecture:**
- PostgreSQL as primary datastore (no ORM recommended for simplicity - use raw SQL or minimal SQLAlchemy)
- Tables: reports, report_images, analyses, notifications, system_logs, portal_credentials
- UUIDs for all primary keys
- JSONB for flexible metadata storage
- Triggers for automatic timestamps (created_at, updated_at)

**Suggested Architecture:**
1. **N8N Role**: Webhook receiver only - triggers Python services, doesn't write to DB
2. **Python Service**: All database writes, authentication, scraping
3. **Credential Management**: Encrypted fields in portal_credentials table, NOT environment variables (allows per-portal config)
4. **Indexing Strategy**: Indexes on created_at, status, email_from for common queries; full-text search on report content for symbol/keyword searches

**Code Patterns to Follow:**
- Use async Playwright pattern from existing scraper
- Use FastAPI + structlog pattern for logging and monitoring
- Use database triggers for automatic timestamp management
- Use JSONB metadata columns to avoid schema migrations for report variants
- Implement retry logic with exponential backoff for transient failures

### Recommendations

**Error States & Retry Strategy** (Concrete Recommendation):
```
Error States:
- scrape_login_failed (login to portal failed)
- scrape_content_failed (URL navigation/extraction failed)
- analysis_timeout (AI API exceeded timeout)
- analysis_error (AI API returned error)
- notification_email_failed
- notification_telegram_failed

Retry Strategy:
- scrape_* errors: 3 attempts with 5-min exponential backoff
- analysis_* errors: 5 attempts over 24 hours (lower priority, async)
- notification_* errors: 3 attempts with 2-min exponential backoff
- After max retries: mark as failed, log event, keep in DB for manual inspection
```

**Deduplication** (Concrete Recommendation):
- **Primary Key**: UNIQUE constraint on (email_message_id)
- **Secondary Check**: Store content_hash (SHA256 of raw_content) to detect forwarded duplicates
- **Version Strategy**: If same report is re-analyzed, store as new analysis row linked to same report, don't create duplicate report
- **Retention**: Keep all report versions for 2 years, then archive to separate "archived_reports" table

**Credential Storage** (Concrete Recommendation):
- Create separate **portal_credentials** table
- Encrypt sensitive columns (username, password) at rest using PostgreSQL pgcrypto extension
- Store per-portal: portal_name, portal_url, username, password_encrypted, created_by, created_at, updated_at
- Support report-level credential override if needed later (add optional credential_id to reports table)
- Never log credentials in system_logs

**Audit Logging** (Concrete Recommendation):
- Log to **system_logs** table with: service_name, log_level, message, report_id, timestamp, metadata (JSON)
- Track events: report_received, login_attempted, login_success/failed, scrape_started/completed/failed, analysis_started/completed, notification_sent/failed
- Include duration metrics (processing time, retry count) in metadata JSONB
- Query logs by report_id or date range for debugging

**Query Performance** (Concrete Recommendation):
- Indexes: created_at DESC, status, email_from, report_url (hash)
- Full-text search: index on raw_content using English dictionary
- JSONB key_trades index using GIN for analysis queries
- Composite index: (status, created_at) for "pending reports sorted by date"
- Partitioning by date after 100k+ reports (not needed now)

**Data Retention** (Concrete Recommendation):
- Keep raw_content and report_images for 2 years
- Create archive tables: archived_reports, archived_images (same schema)
- After 2 years: move to archive tables, soft-delete from active tables
- Keep analysis summaries indefinitely (small size, useful for trends)
- Keep notification logs for 1 year (audit trail)
- Run monthly archival job that moves old data and vacuums indexes

**N8N Integration** (Concrete Recommendation):
- N8N's role: Webhook receiver for incoming emails (ONLY)
- N8N passes email payload to Python API endpoint: POST /api/v1/reports
- Python service handles: parsing, credential lookup, scraping, analysis, notifications, database writes
- Return status to N8N (success/failure for logging in N8N UI)
- DO NOT have N8N write to database directly (keeps auth/encryption logic centralized)
- Webhook callback: Optional - N8N can subscribe to notification_status updates if needed later

**Encryption & Sensitive Data** (Concrete Recommendation):
- Use PostgreSQL pgcrypto: encrypt credentials at rest in portal_credentials table
- Connection: Use SSL for PostgreSQL client connections
- API keys: Store in environment variables (not DB)
- Report content: NO encryption needed (it's your trading analysis, not sensitive)
- Audit: Log access to credentials table (queries, updates) for security

### Database Schema Overview

```
Core Tables:
- reports (id, email_message_id, email_subject, email_from, report_url, raw_content, status, retry_count, created_at)
- report_images (id, report_id, image_url, sequence_order, created_at)
- analyses (id, report_id, summary, key_trades [JSONB], sentiment, confidence_score, ai_provider, created_at)
- notifications (id, analysis_id, channel, recipient, status, sent_at, retry_count, created_at)

Supporting Tables:
- portal_credentials (id, portal_name, portal_url, username, password_encrypted, created_at)
- system_logs (id, service_name, log_level, message, report_id, metadata [JSONB], created_at)

Key Features:
- UUIDs for all IDs
- JSONB for flexible metadata and key_trades
- Triggers for automatic timestamp management
- Indexes on: created_at, status, email_from, content full-text search
- Views for: reports_with_analysis, notification_stats, daily_metrics
```
