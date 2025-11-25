# Specification: Email Webhook Service & Email Parsing

## Goal

Establish a secure HTTP webhook endpoint that receives email payloads from external email service providers, validates and parses email content, detects trading reports based on configurable keywords, extracts URLs pointing to trading portals, and reliably stores normalized email metadata in PostgreSQL. This service is the entry point for the trading report automation pipeline, ensuring only valid, authenticated email events trigger downstream processing.

## User Stories

- As an email service provider (Mailgun, SendGrid), I want to deliver trading report notifications to a secure webhook that validates my signature so that I can be confident the email was received and processed
- As a system operator, I want all incoming emails and parsing errors logged to the database with correlation IDs so that I can audit email processing, trace failures, and maintain compliance
- As the downstream Playwright scraper service, I want reliable, deduplicated email metadata (from, subject, message-ID) stored in PostgreSQL so that I can retrieve report URLs without duplicate processing

## Specific Requirements

**Webhook Endpoint & Request Validation**
- Single POST endpoint at `/webhook/email` accepting JSON payloads from multiple email providers
- HMAC-SHA256 signature verification (primary authentication) using `X-Signature` header and shared secret from environment
- API key fallback authentication via `X-API-Key` header if signature verification is unavailable
- Request body validation using Pydantic models to ensure required fields present (from, subject, email body)
- Reject requests with missing required fields (From, Subject, Message-ID) before processing
- Content-Type must be application/json; return 400 Bad Request for other types

**Email Header Extraction & Parsing**
- Extract and normalize required email headers: From (sender email), Subject (email title), Message-ID (unique identifier), Date (email timestamp in RFC 2822 format)
- Extract optional headers: To (primary recipient), Cc (carbon copy list), Reply-To (reply address)
- Parse both plain text and HTML email body content; prefer plain text if available
- Handle multipart MIME email structures gracefully (extract text/plain or text/html part)
- Store raw email payload (entire JSON) as JSONB in PostgreSQL for audit trail and debugging
- Normalize Date header to ISO 8601 timestamp for consistent database storage

**Report Detection & Keyword Matching**
- Implement case-insensitive keyword matching against email subject and body text
- Load default keywords from environment variable (comma-separated): "trading report", "analysis", "recommendation", "trade alert"
- Support database-driven keyword configuration for runtime updates without service restart (future: read from webhook_config table)
- Return HTTP 202 Accepted on valid email receipt regardless of whether keywords matched (indicates email was processed)
- Log matched keywords to JSONB metadata field for debugging and audit

**URL Extraction & Portal Validation**
- Extract all URLs from email body (plain text and HTML href attributes)
- Filter URLs to only include those matching configured trading portal domain and path patterns
- Default pattern: Domain `protradingskills.com` with path starting with `/analysis`
- Use case-insensitive domain matching (`parsed.netloc.lower()`)
- Use path prefix matching (`parsed.path.startswith()`)
- Validate URL format using urllib.parse before storage (must be valid http or https URL)
- Store only the first valid URL found in report_url field (additional URLs in metadata)
- If no valid URLs found, return 202 but flag in metadata (urls_found: 0) for later review
- Support extensible portal configuration for adding additional domains (future: load from database)

**Rate Limiting & Abuse Prevention**
- Implement per-sender rate limiting: 1 request per second maximum per unique email_from address
- Implement global rate limiting: 100 requests per hour across all senders
- Store rate limit state in PostgreSQL with timestamp tracking (webhook_requests table or similar)
- Return HTTP 429 Too Many Requests when either limit exceeded
- Include `Retry-After` header in 429 response indicating seconds to wait before retry
- Log rate limit violations to system_logs for security monitoring

**Data Storage & Deduplication**
- Write validated email metadata to PostgreSQL reports table
- Use email_message_id as UNIQUE constraint to prevent duplicate ingestion (idempotent operation)
- If duplicate email_message_id received, return 202 with existing report_id (no error, just no-op)
- Set report status to "pending" for newly created reports
- Store email_from (sender email address) for sender filtering and rate limiting
- Store email_subject for report identification and operator review
- Store email_received_at timestamp from Date header (not webhook receipt time)
- Store report_url (first valid portal URL extracted) or NULL if no valid URL found
- Store email_received_at (RFC 2822 formatted timestamp from email Date header)
- Store metadata as JSONB: { keywords_matched: [list], urls_found_count: N, urls_additional: [list], provider: "mailgun|sendgrid|...", raw_payload_hash: "sha256_hash" }
- Record created_at timestamp at webhook receipt time using PostgreSQL NOW()

**Error Handling & Logging**
- Return generic error messages (no technical details) for security; log full errors to system_logs table
- All webhook processing attempts logged to system_logs table with: timestamp, service_name="email-webhook", log_level, message, correlation_id, stack_trace (if error), metadata (JSONB)
- Specific log events: webhook_received, signature_verified, email_parsed, urls_extracted, report_created, rate_limit_exceeded, signature_invalid, malformed_payload
- Generate unique correlation_id (UUID) for each webhook request, include in all logs and return in response
- Different HTTP response codes for different failure modes:
  - 201 Created: New report successfully created and stored
  - 202 Accepted: Valid email received and stored (may be duplicate or no valid URLs found)
  - 400 Bad Request: Malformed JSON payload, missing required fields, invalid email format
  - 401 Unauthorized: Signature verification failed, invalid API key
  - 429 Too Many Requests: Rate limit exceeded (per-sender or global)
  - 500 Internal Server Error: Database connection error, unexpected exception
- Never expose stack traces, SQL errors, or configuration details in API response

**Response Format & Correlation**
- All responses in standardized JSON format with: success (boolean), status (string), report_id (UUID), correlation_id (UUID), message (string), timestamp (ISO 8601)
- Success response (201/202): `{"success": true, "status": "created|accepted", "report_id": "uuid", "correlation_id": "uuid", "message": "Email processed successfully", "timestamp": "2025-11-25T10:30:00Z"}`
- Error response (400/401/429/500): `{"success": false, "status": "rejected|failed", "error": "Generic error message", "correlation_id": "uuid", "timestamp": "2025-11-25T10:30:00Z"}`
- Include rate limit information in response headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)

**Health Check Endpoint**
- GET `/health` endpoint for service monitoring and orchestration
- Response: `{"status": "ok", "timestamp": "2025-11-25T10:30:00Z", "database": "connected"}`
- Verify database connectivity before returning success
- Return 503 Service Unavailable if database unreachable

**Multi-Provider Support**
- Design webhook endpoint as generic handler accepting JSON payloads from any email provider
- Support Mailgun format (email fields: from, subject, stripped-text, timestamp, message-id, X-Signature header)
- Support SendGrid format (email fields: from, subject, text, timestamp, message_id, X-Twilio-Email-Event-Webhook-Signature header)
- Use adapter pattern internally to normalize different provider payloads to standard format (future: if more providers added)
- Document required webhook configuration for each provider (signature secret, field mapping, header names)

## Visual Design

No visual mockups provided for this service. This is a backend webhook endpoint with no UI component.

Data flow diagram:

```
Email Provider (Mailgun/SendGrid/etc.)
         |
         v (HTTPS POST with signature)
    Webhook Endpoint (/webhook/email)
         |
         +---> Signature Verification (HMAC-SHA256 or API Key)
         |
         +---> Email Parsing (headers, body, URLs)
         |
         +---> Rate Limiting Check (per-sender, global)
         |
         +---> URL Extraction & Validation
         |
         +---> Deduplication (message-id lookup)
         |
         v
    PostgreSQL reports table
         |
         v (N8N polls)
    Downstream Services (Scraper, Analyzer, Notification)
```

## Existing Code to Leverage

**URL Extraction Pattern from refs/scraper.py and playwright-service/scraper.py**
- Existing code uses `urllib.parse.urlparse()` for URL parsing with case-insensitive domain matching
- Pattern: `parsed.netloc.lower() == "protradingskills.com"` for domain validation
- Pattern: `parsed.path.startswith("/analysis")` for path prefix matching
- Already handles multiple URLs in scraped content
- Can directly import and reuse this extraction logic in webhook service
- This pattern is proven, tested, and aligns with project conventions

**PostgreSQL Schema from agent-os/specs/2025-11-25-postgresql-schema-data-persistence/spec.md**
- `reports` table already designed with all required fields: id (UUID), email_from, email_subject, email_message_id (UNIQUE), email_received_at, report_url, status, metadata (JSONB), created_at, updated_at
- `system_logs` table for audit trail: id, service_name, log_level, message, correlation_id, stack_trace, metadata (JSONB), created_at
- Existing timestamp patterns (created_at, updated_at, processed_at) for consistency
- JSONB metadata pattern for flexible, extensible attributes
- Use existing database models and patterns; no schema changes required

**FastAPI Framework Conventions from CLAUDE.md**
- Use FastAPI with Pydantic models for request/response validation
- Async/await pattern for non-blocking I/O operations
- Consistent health check endpoint pattern `/health`
- Environment variable configuration via os.environ or python-dotenv
- Structured logging patterns with context and correlation IDs
- Error handling with specific exception types and clear boundaries

**Error Handling Pattern from agent-os/standards/global/error-handling.md**
- Use specific exception types rather than generic Exception
- Log errors with full context (service_name, correlation_id, metadata) to system_logs table
- Return generic messages to clients (no stack traces or technical details)
- Implement centralized error handling at API layer boundary
- Clean up database connections in finally blocks or async context managers

**Validation Pattern from agent-os/standards/global/validation.md**
- Server-side validation using Pydantic models (BaseModel for request/response)
- Validate input at earliest point (webhook handler) before processing
- Use specific, field-level validation errors
- Sanitize input to prevent injection attacks (parameterized queries for rate limit tracking)
- Business rule validation (signature, rate limits) at appropriate layer

## Out of Scope

- Email sending or SMTP server implementation (handled by notification service)
- Report scraping or content extraction from portal URLs (handled by Playwright scraper service)
- AI analysis or summarization of report content (handled by AI analyzer service)
- Telegram notifications or SMS delivery (handled by notification service)
- Email attachment processing, file storage, or binary data extraction
- Manual webhook signature generation or key management UI (configuration via environment variables only)
- Alternative authentication methods beyond HMAC-SHA256 and API key (OAuth, mTLS, etc.)
- Webhook retry logic or dead-letter queue management (provider responsibility)
- Email address validation via DNS/SMTP verification
- Advanced HTML-to-text conversion beyond basic multipart parsing
- N8N workflow orchestration configuration or N8N integration (configured separately in N8N UI)
- User authentication or multi-tenant support (single-user homelab deployment)
- Request body size limits beyond FastAPI defaults (tune if needed but not a focus)
- Custom rate limiting algorithms or Redis integration (PostgreSQL sufficient for Phase 1)
