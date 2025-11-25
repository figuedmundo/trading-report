# Spec Requirements: Email Webhook Service

## Initial Description

Build an HTTP webhook service that receives email payloads from an external email service provider, parses email content, detects trading reports based on configurable keywords, extracts URLs pointing to trading portals, and validates the incoming webhook requests. This service is the entry point for the trading report automation pipeline.

## Requirements Discussion

### First Round Questions

**Q1:** Should the webhook endpoint be generic to handle multiple email providers (Mailgun, SendGrid, Gmail, etc.) or optimized for a single provider initially?
**Answer:** Generic endpoint supporting multiple providers. The design should be extensible to different payload formats without code changes, but we'll prioritize Mailgun and SendGrid initially.

**Q2:** For signature verification, should we use HMAC-SHA256 (Mailgun/SendGrid standard) with an API key fallback, or explore alternative authentication methods?
**Answer:** Yes, HMAC-SHA256 as primary with API key fallback. This covers industry standards and provides flexibility for different provider approaches.

**Q3:** Which email headers are absolutely required (From, Subject, Message-ID, Date) vs. optional metadata (To, Cc, Reply-To)?
**Answer:** Required: From, Subject, Message-ID, Date. Optional: To, Cc, Reply-To. This provides sufficient metadata for report tracking and deduplication while keeping parsing flexible.

**Q4:** Should keyword matching for report detection be hardcoded, configurable at startup, or dynamically configurable from the database?
**Answer:** Dynamically configurable from PostgreSQL. Default keywords: "trading report", "analysis", "recommendation", "trade alert". This allows runtime updates without service restarts.

**Q5:** For URL extraction, should we extract all URLs or filter by specific domain/path patterns? Should this filtering be configurable?
**Answer:** Filter by domain and path patterns. Pattern: Domain must be `protradingskills.com` with path starting with `/analysis`. This should be extensible for additional portal domains configured in the database.

**Q6:** Should rate limiting be per-sender (prevent one source flooding) and/or global (protect overall system)? What are reasonable limits?
**Answer:** Both. Per-sender: 1 request per second. Global: 100 requests per hour. Track in PostgreSQL or memory cache. Return HTTP 429 when exceeded.

**Q7:** For error responses, should we return detailed error messages for debugging or generic messages for security?
**Answer:** Generic messages for security. All errors logged to `system_logs` table in PostgreSQL. Only return HTTP 202 (Accepted) on valid receipt with a report_id, regardless of whether a trading report was detected.

**Q8:** Should the service parse email attachments, or focus only on headers and body content?
**Answer:** Focus on headers and body (text/HTML). Attachment processing is out of scope and can be added later if needed. Store raw email payload for audit trail.

### Existing Code to Reference

**Similar Features Identified:**
- Feature: URL Extraction Pattern - Path: `app/extractor.py`
  - Reference code: Domain-specific URL validation using `parsed.netloc.lower()` and `parsed.path.startswith()`
  - Components to reuse: Case-insensitive domain matching, path prefix validation pattern
  - Backend logic to reference: Python `urllib.parse` pattern for selective URL extraction

**Database Integration:**
- Path: `agent-os/specs/2025-11-25-postgresql-schema-data-persistence/spec.md`
  - Reference schema: `reports` table, `system_logs` table, webhook_config table
  - Existing models to leverage: PostgreSQL audit trail patterns, JSON metadata storage

### Follow-up Questions

**Follow-up 1:** For rate limiting tracking, should we use PostgreSQL (persistent across restarts) or in-memory cache (faster but lost on restart)?
**Answer:** Use PostgreSQL for rate limit tracking to persist across service restarts and maintain accurate per-sender/global counts in production homelab environment.

**Follow-up 2:** Should the webhook accept only POST requests or support other HTTP methods (GET for health checks, etc.)?
**Answer:** POST for `/webhook` endpoint. Separate `/health` endpoint for health checks following FastAPI conventions from the tech-stack.

## Visual Assets

### Files Provided:
No visual assets provided.

## Requirements Summary

### Functional Requirements

- Receive email payloads via HTTP POST webhook from external email service providers
- Validate incoming webhook requests using HMAC-SHA256 signature verification with API key fallback
- Extract required email headers: From, Subject, Message-ID, Date
- Extract optional email metadata: To, Cc, Reply-To
- Detect trading reports using configurable keyword matching (case-insensitive)
- Extract and filter URLs matching trading portal patterns (domain + path validation)
- Parse plain text and HTML email bodies
- Handle multipart MIME email structures
- Store raw email payload for audit trail and compliance
- Rate limit requests: 1 per second per sender, 100 per hour globally
- Return HTTP 202 with report_id on valid webhook receipt
- Return HTTP 429 when rate limits exceeded
- Log all errors (invalid signature, missing headers, parsing failures, rate limits) to system_logs table
- Return generic error messages (no detailed debugging info for security)
- Provide standard JSON response format with status and report_id

### Reusability Opportunities

- URL extraction logic can reuse pattern from `app/extractor.py` for domain/path validation
- PostgreSQL integration can reference existing `reports` and `system_logs` table patterns
- FastAPI health check endpoint follows conventions established in tech-stack.md
- Pydantic model validation patterns from existing project code standards
- Error handling and logging patterns from `agent-os/standards/global/error-handling.md`

### Scope Boundaries

**In Scope:**
- HTTP webhook endpoint listening on POST `/webhook`
- HMAC-SHA256 signature verification with API key fallback
- Email header extraction (required and optional)
- Keyword matching for report detection with database-driven configuration
- Selective URL extraction with domain/path pattern filtering
- Email body parsing (text and HTML multipart)
- Raw email payload storage for audit trail
- Rate limiting (per-sender and global) with PostgreSQL tracking
- Error logging to system_logs table
- Standard JSON response format
- Health check endpoint (`/health`)
- Docker containerization following project patterns

**Out of Scope:**
- Email sending or SMTP server implementation (handled by notification service)
- Report scraping/content extraction from URLs (handled by Playwright scraper service)
- AI analysis of report content (handled by AI analyzer service)
- Telegram notifications (handled by notification service)
- Email attachment processing or file storage
- Manual signature generation or webhook key management UI
- Alternative authentication beyond HMAC-SHA256 and API key
- Webhook retry logic or dead-letter queue management
- Email address validation or DNS verification
- HTML-to-text conversion optimization beyond basic parsing
- N8N workflow orchestration configuration

### Technical Considerations

- **Framework**: FastAPI (async HTTP, auto-documentation with Pydantic)
- **Language**: Python 3.11+
- **Database**: PostgreSQL 15+ for configuration, rate limiting, and error logging
- **Signature Verification**: Use `cryptography` library for HMAC-SHA256
- **Email Parsing**: Python `email` module (standard library) for MIME handling
- **URL Parsing**: Python `urllib.parse` for selective domain/path extraction
- **Rate Limiting**: PostgreSQL with timestamp-based tracking
- **Validation**: Pydantic models for request/response schemas
- **Logging**: Structured logging to system_logs PostgreSQL table
- **Deployment**: Docker container with environment-based configuration
- **Healthcheck**: `/health` endpoint returning `{"status": "ok"}`

### Integration Points

- **Upstream Input**: Email service provider webhooks (Mailgun, SendGrid, Gmail)
- **Downstream Output**: N8N workflow engine (webhook trigger for scraper/analyzer/notification orchestration)
- **Database**: PostgreSQL tables - `reports`, `system_logs`, `webhook_config`
- **Configuration**: Runtime keyword matching from `webhook_config` table
- **Rate Limiting**: PostgreSQL `webhook_requests` or similar tracking table
- **Error Tracking**: PostgreSQL `system_logs` table with structured error details

### Success Criteria

1. Webhook endpoint validates HMAC-SHA256 signatures correctly and rejects invalid requests
2. Trading reports identified using configurable keywords from database
3. Portal URLs extracted and filtered according to domain/path patterns
4. Rate limiting enforced at both per-sender (1/sec) and global (100/hr) levels
5. All errors logged to system_logs with context (sender, timestamp, error type)
6. Service returns HTTP 202 with report_id on valid receipt
7. Response time for webhook processing under 500ms
8. Zero credential exposure in logs or error responses
9. Integration with PostgreSQL schema works seamlessly
10. Service deployment via Docker with health check endpoint
