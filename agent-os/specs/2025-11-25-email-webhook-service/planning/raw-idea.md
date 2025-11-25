# Email Webhook Service - Raw Idea

## Feature Overview

Build an HTTP webhook service that receives email payloads from an external email service provider, parses email content, detects trading reports based on configurable keywords, extracts URLs pointing to trading portals, and validates the incoming webhook requests.

This service is the entry point for the trading report automation pipeline, sitting upstream of the Playwright scraper service.

## Confirmed Requirements & Decisions

### 1. Generic Webhook Endpoint
- Single `/webhook` endpoint supporting multiple email providers
- Extensible to handle Mailgun, SendGrid, Gmail webhooks without code changes
- Provider-agnostic design with configurable payload parsing

### 2. Security & Signature Verification
- Primary: HMAC-SHA256 signature verification (industry-standard for email webhooks)
- Fallback: API key validation header
- Signature extraction method matches provider standards (Mailgun, SendGrid formats)
- Rate limiting: 1 request per second per sender; 100 requests per hour globally

### 3. Email Header Requirements
**Required headers:**
- From: Sender's email address
- Subject: Email subject line
- Message-ID: Unique identifier for deduplication
- Date: Email timestamp

**Optional metadata:**
- To: Primary recipient
- Cc: Carbon copy recipients
- Reply-To: Reply address for responses

### 4. Keyword Matching & Report Detection
- Configurable keyword matching (case-insensitive)
- Default keywords: "trading report", "analysis", "recommendation", "trade alert"
- Configuration stored in PostgreSQL for runtime updates
- Flexible pattern matching to identify trading emails without manual review

### 5. URL Extraction & Filtering
- Selective URL extraction using domain and path validation
- Pattern: Domain `protradingskills.com` + path starts with `/analysis`
- Reference implementation from existing `app/extractor.py`:
  ```python
  if parsed.netloc.lower() == "protradingskills.com" and parsed.path.startswith("/analysis"):
      urls.append(href)
  ```
- Extensible for additional portal domains
- Only extract URLs matching trading portal patterns (security and noise reduction)

### 6. Email Parsing & Content Extraction
- Extract plain text and HTML body
- Parse email headers and metadata
- Handle multipart MIME structures
- Store raw email payload for audit trail

### 7. Error Handling & Logging
- Graceful error handling with structured logging
- All errors logged to `system_logs` table in PostgreSQL
- Errors include: invalid signature, missing headers, parsing failures, rate limit violations
- No user-facing error messages for security
- Return HTTP 202 (Accepted) on valid receipt, regardless of report detection

### 8. Rate Limiting
- Per-sender limit: 1 request per second (prevent single source flooding)
- Global limit: 100 requests per hour (prevent total system overload)
- Rate limit tracking in PostgreSQL or memory cache
- Return HTTP 429 (Too Many Requests) when exceeded

### 9. Response Format
Standard JSON response format:
```json
{
  "status": "received",
  "report_id": "unique-identifier",
  "message": "Email processing queued"
}
```

### 10. Scope Boundaries

**In Scope:**
- HTTP webhook endpoint with signature verification
- Email payload parsing and header extraction
- Keyword matching for report detection
- URL filtering and extraction for portal access
- Rate limiting and error logging
- Standard JSON response format
- Integration with PostgreSQL for configuration and logging
- Secure webhook signature handling

**Out of Scope:**
- Email sending (handled by notification service)
- Report scraping from portal URLs (handled by Playwright scraper service)
- AI analysis of report content (handled by AI analyzer service)
- Telegram notifications (handled by notification service)
- Manual webhook signature generation or key management UI
- Alternative authentication methods beyond HMAC and API key
- Webhook retry logic or dead-letter queue management
- Email address validation or DNS verification
- Attachment processing or file storage
- HTML-to-text conversion optimization
- N8N workflow orchestration (configured separately)

## Architecture Context

### System Position
This service is **Phase 1 MVP** component, positioned at the beginning of the trading report processing pipeline:

```
Email Event → Webhook Service → [N8N Orchestration] → Playwright Scraper → AI Analyzer → Notification Service
```

### Technology Stack Reference
- **Framework**: FastAPI (async HTTP)
- **Language**: Python 3.11+
- **Database**: PostgreSQL 15+
- **Validation**: Pydantic models
- **Signature Verification**: cryptography library
- **Deployment**: Docker container

### Existing Patterns to Follow
- Leverage existing PostgreSQL schema and models from `database_schema.sql`
- Follow FastAPI conventions from tech-stack.md
- Apply error handling patterns from project standards
- Reference URL extraction logic from `app/extractor.py`

### Integration Points
- **Upstream**: Email service provider webhooks (Mailgun, SendGrid, etc.)
- **Downstream**: N8N workflow engine (via webhook trigger)
- **Database**: PostgreSQL tables: `reports`, `system_logs`, `webhook_config`
- **Configuration**: Runtime-configurable keywords in database

## Success Criteria

1. Webhook receives and validates email payloads correctly
2. Trading reports detected with configurable keywords
3. Portal URLs extracted and filtered securely
4. Rate limiting prevents abuse
5. All errors logged for audit trail
6. Service returns standard JSON responses
7. Signature verification prevents unauthorized access
8. Integration with PostgreSQL schema works seamlessly
9. Performance: Handle webhook requests within 500ms
10. Zero data loss or credential exposure in error logs
