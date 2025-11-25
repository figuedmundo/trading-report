# Task Breakdown: Email Webhook Service & Email Parsing

## Overview

Total Tasks: 32 core implementation tasks organized into 6 phases

This document outlines the strategic implementation plan for the Email Webhook Service, the entry point to the trading report automation pipeline. The service receives email payloads from providers (Mailgun, SendGrid), validates signatures, parses email content, detects trading reports, extracts URLs, and stores metadata in PostgreSQL for downstream processing.

## Task List

### Phase 1: Project Setup & Core Infrastructure

**Dependencies:** None

#### Task Group 1: Service Directory Structure & FastAPI Scaffold

- [x] 1.0 Complete project setup and FastAPI scaffold
  - [x] 1.1 Write 4-6 focused tests for FastAPI app initialization and health check
    - Test service starts without errors
    - Test GET /health endpoint returns 200 with correct schema
    - Test GET /health returns database_connected: true/false
    - Test database connection pooling initializes correctly
    - Limit to critical startup and health check behaviors only
  - [x] 1.2 Create service directory structure
    - Create `services/email-webhook/` directory
    - Create subdirectories: `src/`, `tests/`, `docs/`
    - Follow pattern from CLAUDE.md service guidelines
  - [x] 1.3 Initialize FastAPI application scaffold
    - Create `src/main.py` with FastAPI app initialization
    - Implement GET `/health` endpoint per spec
    - Set app title: "Email Webhook Service", version "0.1.0"
    - Configure CORS headers for webhook providers
    - Follow FastAPI conventions from existing project
  - [x] 1.4 Set up Pydantic models for request/response validation
    - Create `src/models.py`
    - Define `WebhookRequest` base model (supports multiple provider formats)
    - Define `WebhookResponse` model with success/error variants
    - Define `HealthResponse` model
    - Reference patterns from `agent-os/standards/backend/models.md`
  - [x] 1.5 Ensure infrastructure tests pass
    - Run only the 4-6 tests written in 1.1
    - Verify FastAPI app initializes correctly
    - Verify health check endpoint works
    - Verify database connection pooling is configured
    - Do NOT run entire test suite

**Acceptance Criteria:**
- The 4-6 tests written in 1.1 pass
- Service directory structure created correctly
- FastAPI app starts without errors
- Health check endpoint returns proper response format
- Database connection configured (tested in phase 2)

---

#### Task Group 2: Environment Configuration & Database Connectivity

**Dependencies:** Task Group 1

- [x] 2.0 Complete environment and database setup
  - [x] 2.1 Write 3-4 focused tests for database connectivity
    - Test database connection with valid credentials
    - Test health check verifies database connectivity
    - Test connection pooling configuration
    - Limit to critical database connection behaviors
  - [x] 2.2 Create environment configuration system
    - Create `.env.example` with required variables (reference: CLAUDE.md)
    - Implement environment variable loading via `python-dotenv`
    - Create `src/config.py` for configuration management
    - Document required variables:
      - `DATABASE_URL`: PostgreSQL connection string
      - `WEBHOOK_SIGNATURE_SECRET`: HMAC-SHA256 shared secret
      - `API_KEY_FALLBACK`: Optional API key for fallback auth
      - `REPORT_KEYWORDS`: Comma-separated list (default: "trading report,analysis,recommendation,trade alert")
      - `TRUSTED_DOMAINS`: Comma-separated trusted portal domains (default: "protradingskills.com")
      - `RATE_LIMIT_PER_SECOND`: Per-sender rate limit (default: 1)
      - `RATE_LIMIT_PER_HOUR`: Global rate limit (default: 100)
      - `LOG_LEVEL`: Logging verbosity (default: "INFO")
  - [x] 2.3 Set up PostgreSQL database connectivity
    - Implement connection pooling (psycopg2.pool.ThreadedConnectionPool)
    - Create `src/database.py` for database operations
    - Implement connection context manager for safe resource cleanup
    - Use pattern from `agent-os/standards/backend/queries.md`
  - [x] 2.4 Verify database layer connectivity
    - Confirm connection pool initializes at startup
    - Test GET /health queries database for connectivity status
    - Verify connection pooling works correctly
  - [x] 2.5 Ensure database connectivity tests pass
    - Run only the 3-4 tests written in 2.1
    - Verify database connections succeed/fail appropriately
    - Verify health check includes database status
    - Do NOT run entire test suite

**Acceptance Criteria:**
- The 3-4 tests written in 2.1 pass
- Environment variables properly loaded from .env
- Database connection pool initialized successfully
- Health check endpoint queries database status
- Connection context managers prevent leaks

---

### Phase 2: Webhook Endpoint & Request Handling

**Dependencies:** Task Group 1-2

#### Task Group 3: Webhook Endpoint & HMAC-SHA256 Signature Verification

- [x] 3.0 Complete webhook endpoint with signature verification
  - [x] 3.1 Write 5-6 focused tests for webhook signature verification
    - Test valid HMAC-SHA256 signature accepted
    - Test invalid signature rejected with 401
    - Test missing X-Signature header rejected
    - Test API key fallback authentication
    - Test generic error message (no technical details)
    - Limit to critical security and auth behaviors
  - [x] 3.2 Implement HMAC-SHA256 signature verification
    - Create `src/security.py` for security operations
    - Implement signature verification function:
      - Read `X-Signature` header from request
      - Compute HMAC-SHA256 of request body using shared secret
      - Compare with provided signature (constant-time comparison)
      - Return True/False for validity
    - Reference: spec section "Webhook Endpoint & Request Validation"
  - [x] 3.3 Implement API key fallback authentication
    - Check `X-API-Key` header if signature verification unavailable
    - Compare against `API_KEY_FALLBACK` environment variable
    - Use as secondary authentication method
    - Log authentication method used for audit trail
  - [x] 3.4 Create POST /webhook/email endpoint
    - Accept JSON payloads from email providers
    - Validate Content-Type: application/json (400 if not)
    - Generate unique correlation_id (UUID) for each request
    - Call signature verification before processing
    - Return 401 Unauthorized if both signature and API key fail
    - Return generic error message (no stack traces)
    - Log all authentication attempts to system_logs
  - [x] 3.5 Implement proper HTTP response codes
    - 201 Created: New report successfully created
    - 202 Accepted: Valid email received (may be duplicate)
    - 400 Bad Request: Malformed JSON or missing required fields
    - 401 Unauthorized: Signature/API key verification failed
    - 429 Too Many Requests: Rate limit exceeded
    - 500 Internal Server Error: Unexpected exception (generic message)
  - [x] 3.6 Ensure webhook endpoint tests pass
    - Run only the 5-6 tests written in 3.1
    - Verify signature verification logic works correctly
    - Verify API key fallback works
    - Verify generic error messages (no technical details)
    - Do NOT run entire test suite

**Acceptance Criteria:**
- The 5-6 tests written in 3.1 pass
- HMAC-SHA256 signature verification works correctly
- API key fallback authentication implemented
- All endpoints return proper HTTP status codes
- Generic error messages with no technical details
- Correlation ID generated for traceability

---

#### Task Group 4: Request Parsing & Pydantic Validation

**Dependencies:** Task Group 3

- [x] 4.0 Complete request parsing and validation
  - [x] 4.1 Write 5-6 focused tests for request parsing and validation
    - Test valid Mailgun format parsed correctly
    - Test valid SendGrid format parsed correctly
    - Test missing required fields rejected with 400
    - Test optional fields handled gracefully
    - Test invalid email format rejected
    - Limit to critical parsing and validation behaviors
  - [x] 4.2 Extend Pydantic models for provider formats
    - Create provider-specific request models:
      - `MailgunPayload`: from, subject, stripped-text, timestamp, message-id, etc.
      - `SendGridPayload`: from, subject, text, timestamp, message_id, etc.
    - Define required fields: from, subject, body/text, message-id/message_id
    - Define optional fields: to, cc, reply-to, html
    - Use Pydantic field validation for format checks
  - [x] 4.3 Implement email header extraction
    - Create `src/parsers.py` for email parsing logic
    - Extract required headers: From, Subject, Message-ID, Date
    - Extract optional headers: To, Cc, Reply-To
    - Normalize email addresses (lowercase, strip whitespace)
    - Convert Date header to ISO 8601 timestamp
    - Handle RFC 2822 format dates (email standard)
  - [x] 4.4 Implement multipart MIME handling
    - Parse both plain text and HTML email bodies
    - Prefer plain text if available, fall back to HTML
    - Extract text from HTML (basic stripping of tags)
    - Store raw payload (entire JSON) as JSONB for audit
  - [x] 4.5 Validate request at earliest point
    - Apply Pydantic validation in webhook handler
    - Return 400 Bad Request with field-level errors for invalid input
    - Log validation failures to system_logs
    - Follow pattern from `agent-os/standards/global/validation.md`
  - [x] 4.6 Ensure parsing tests pass
    - Run only the 5-6 tests written in 4.1
    - Verify both Mailgun and SendGrid formats parsed
    - Verify required fields enforced
    - Verify header extraction works correctly
    - Do NOT run entire test suite

**Acceptance Criteria:**
- The 5-6 tests written in 4.1 pass
- Both Mailgun and SendGrid formats supported
- All required fields validated
- Email headers correctly extracted and normalized
- Multipart MIME handling works
- Request validation at boundary (webhook handler)

---

### Phase 3: Email Parsing & Extraction Logic

**Dependencies:** Task Group 4

#### Task Group 5: Keyword-Based Report Detection

**Dependencies:** Task Group 4

- [x] 5.0 Complete keyword-based report detection
  - [x] 5.1 Write 4-5 focused tests for keyword matching
    - Test keyword match found in subject (case-insensitive)
    - Test keyword match found in body (case-insensitive)
    - Test no keywords found returns 202 with metadata
    - Test custom keywords loaded from environment
    - Limit to critical keyword detection behaviors
  - [x] 5.2 Implement configurable keyword loading
    - Load keywords from `REPORT_KEYWORDS` environment variable
    - Parse comma-separated list into array
    - Store keywords in memory (loaded at startup)
    - Provide function to reload keywords without restart (future)
  - [x] 5.3 Implement keyword matching logic
    - Create `src/detection.py` for report detection
    - Implement case-insensitive matching against subject and body
    - Match whole words or phrase substrings (configurable)
    - Track matched keywords in list
    - Return matched keywords for metadata logging
  - [x] 5.4 Handle no-match scenario
    - Return HTTP 202 Accepted (not 200 or 400)
    - Store report with keywords_matched: [] in metadata
    - Flag in metadata: report_detection_status: "no_keywords_matched"
    - Log event: "Email received but no trading keywords detected"
  - [x] 5.5 Ensure keyword detection tests pass
    - Run only the 4-5 tests written in 5.1
    - Verify case-insensitive matching works
    - Verify empty keyword list handled
    - Verify metadata contains matched keywords
    - Do NOT run entire test suite

**Acceptance Criteria:**
- The 4-5 tests written in 5.1 pass
- Keywords loaded from environment variable
- Case-insensitive matching works correctly
- Matched keywords tracked in metadata
- No-match scenario returns 202 (not error)

---

#### Task Group 6: URL Extraction & Portal Validation

**Dependencies:** Task Group 5

- [x] 6.0 Complete URL extraction and portal validation
  - [x] 6.1 Write 5-7 focused tests for URL extraction
    - Test valid portal URL extracted from plain text
    - Test valid portal URL extracted from HTML href
    - Test non-trusted domain rejected
    - Test invalid URL format rejected
    - Test multiple URLs with first valid one selected
    - Test no valid URLs returns 202 with metadata
    - Limit to critical URL extraction behaviors
  - [x] 6.2 Implement URL extraction from email body
    - Create `src/extractors.py` for URL extraction (reuse pattern from refs/scraper.py)
    - Extract all URLs from plain text body (regex pattern: https?://[^\s]+)
    - Extract all URLs from HTML href attributes (parse <a> tags)
    - Validate URL format using urllib.parse.urlparse()
    - Return list of extracted URLs
  - [x] 6.3 Implement portal domain/path filtering
    - Load trusted domains from `TRUSTED_DOMAINS` environment variable
    - Default: "protradingskills.com" with path "/analysis"
    - Implement case-insensitive domain matching: `parsed.netloc.lower()`
    - Implement path prefix matching: `parsed.path.startswith()`
    - Support multiple domain/path pairs (comma-separated config)
  - [x] 6.4 Handle URL validation & selection
    - Validate each extracted URL (must be http or https)
    - Filter URLs matching trusted domain/path patterns
    - Select first valid URL for report_url field
    - Store additional valid URLs in metadata: urls_additional
    - Store count of found URLs: urls_found_count
    - Handle no valid URLs scenario gracefully
  - [x] 6.5 Handle no-URL scenario
    - If no valid URLs found, return HTTP 202 Accepted
    - Set report_url to NULL (optional field)
    - Log: urls_found_count: 0 in metadata
    - Flag in metadata: urls_extracted: false
    - Log event: "Email processed but no valid portal URLs found"
  - [x] 6.6 Ensure URL extraction tests pass
    - Run only the 5-7 tests written in 6.1
    - Verify extraction from plain text and HTML
    - Verify domain/path filtering works
    - Verify multiple URLs handled correctly
    - Verify no-URL scenario returns 202
    - Do NOT run entire test suite

**Acceptance Criteria:**
- The 5-7 tests written in 6.1 pass
- URLs extracted from plain text and HTML
- Trusted domain/path filtering works correctly
- First valid URL selected for report_url
- Additional URLs stored in metadata
- No-URL scenario returns 202 (not error)

---

### Phase 4: Data Storage & Database Integration

**Dependencies:** Task Group 6

#### Task Group 7: PostgreSQL Integration & Report Insertion

**Dependencies:** Task Group 6

- [x] 7.0 Complete data storage and database integration
  - [x] 7.1 Write 4-5 focused tests for database operations
    - Test new report inserted correctly
    - Test duplicate email_message_id returns existing report_id (202)
    - Test report_url NULL handled when no URLs found
    - Test metadata JSONB stored correctly
    - Limit to critical database insertion behaviors
  - [x] 7.2 Map email metadata to database fields
    - Create `src/storage.py` for database write operations
    - Map extraction results to reports table:
      - email_from: Extracted from email
      - email_subject: Extracted from email
      - email_message_id: Extracted from email (UNIQUE constraint)
      - email_received_at: Parsed from Date header (ISO 8601)
      - report_url: First valid portal URL (or NULL)
      - status: Set to "pending" for all new reports
      - created_at: Set by PostgreSQL NOW()
      - updated_at: Set by PostgreSQL NOW()
    - Reference pattern from `agent-os/specs/2025-11-25-postgresql-schema-data-persistence/spec.md`
  - [x] 7.3 Prepare JSONB metadata payload
    - Build metadata dictionary:
      - keywords_matched: [list of matched keywords or empty]
      - urls_found_count: Number of valid URLs found
      - urls_additional: [list of additional valid URLs]
      - provider: "mailgun" | "sendgrid" (detected from headers)
      - raw_payload_hash: SHA256 hash of raw JSON payload
      - webhook_received_at: ISO 8601 timestamp
    - Store raw payload as text field (optional, for audit)
  - [x] 7.4 Implement INSERT operation with deduplication
    - Use email_message_id as UNIQUE constraint (database enforces)
    - Attempt INSERT with all extracted data
    - If duplicate email_message_id:
      - Catch unique constraint violation
      - Query for existing report by email_message_id
      - Return existing report_id in response (202 Accepted)
      - Log: "Duplicate email processed, returning existing report"
    - If success: Return newly created report_id (201 Created)
    - Use parameterized queries to prevent SQL injection
  - [x] 7.5 Implement database error handling
    - Wrap database operations in try-except
    - Catch connection errors (database down)
    - Catch constraint violations (duplicate or data errors)
    - Return appropriate HTTP status codes:
      - 500 Internal Server Error for connection failures
      - 202 Accepted for duplicates (idempotent)
      - 400 Bad Request for data validation errors
    - Log full errors to system_logs with correlation_id
    - Return generic error message to client
    - Follow pattern from `agent-os/standards/global/error-handling.md`
  - [x] 7.6 Ensure database insertion tests pass
    - Run only the 4-5 tests written in 7.1
    - Verify INSERT operations work correctly
    - Verify duplicate handling returns existing report_id
    - Verify metadata stored as JSONB
    - Verify error handling returns proper status codes
    - Do NOT run entire test suite

**Acceptance Criteria:**
- The 4-5 tests written in 7.1 pass
- Email metadata correctly mapped to database
- JSONB metadata prepared with all required fields
- Deduplication via email_message_id works
- Duplicate emails return existing report_id (202)
- Database errors handled gracefully
- Parameterized queries prevent SQL injection

---

### Phase 5: Security, Rate Limiting & Error Handling

**Dependencies:** Task Group 7

#### Task Group 8: Rate Limiting Implementation

**Dependencies:** Task Group 7

- [x] 8.0 Complete rate limiting and security controls
  - [x] 8.1 Write 4-5 focused tests for rate limiting
    - Test per-sender rate limit enforced (1 req/sec)
    - Test global rate limit enforced (100 req/hour)
    - Test 429 Too Many Requests response
    - Test Retry-After header included in 429
    - Limit to critical rate limiting behaviors
  - [x] 8.2 Implement per-sender rate limiting
    - Create rate limiting table in PostgreSQL (or use in-memory cache for Phase 1)
    - Track requests per email_from address with timestamp
    - Limit: 1 request per second per sender
    - Check before processing webhook:
      - Query webhook_requests table for email_from
      - Count requests in last 1 second
      - If count >= 1: Return 429 Too Many Requests
    - Log rate limit violation to system_logs
  - [x] 8.3 Implement global rate limiting
    - Track all webhook requests globally with timestamp
    - Limit: 100 requests per hour across all senders
    - Check before processing webhook:
      - Query webhook_requests for requests in last 3600 seconds
      - Count total requests
      - If count >= 100: Return 429 Too Many Requests
    - Log rate limit violation to system_logs
  - [x] 8.4 Implement rate limit response headers
    - Include rate limit information in all responses:
      - `X-RateLimit-Limit`: Maximum requests allowed
      - `X-RateLimit-Remaining`: Requests remaining in current window
      - `X-RateLimit-Reset`: Unix timestamp when limit resets
    - For 429 response, include `Retry-After` header (seconds to wait)
  - [x] 8.5 Implement webhook_requests tracking
    - Create webhook_requests table or use in-memory dict (Phase 1):
      - email_from: sender email address
      - timestamp: request timestamp
      - status: success | rejected (for monitoring)
    - Insert record for each webhook attempt
    - Clean up old records (older than 1 hour) to prevent memory growth
  - [x] 8.6 Ensure rate limiting tests pass
    - Run only the 4-5 tests written in 8.1
    - Verify per-sender rate limit enforced
    - Verify global rate limit enforced
    - Verify 429 response with Retry-After header
    - Verify rate limit headers in success responses
    - Do NOT run entire test suite

**Acceptance Criteria:**
- The 4-5 tests written in 8.1 pass
- Per-sender rate limiting works (1 req/sec)
- Global rate limiting works (100 req/hour)
- 429 responses include Retry-After header
- Rate limit violations logged to system_logs
- Rate limit headers in all responses

---

#### Task Group 9: Error Handling & System Logging

**Dependencies:** Task Group 8

- [x] 9.0 Complete error handling and audit logging
  - [x] 9.1 Write 5-6 focused tests for error handling and logging
    - Test malformed JSON returns 400
    - Test missing required fields returns 400
    - Test database errors return 500
    - Test all errors logged to system_logs
    - Test correlation_id included in all logs
    - Limit to critical error and logging behaviors
  - [x] 9.2 Implement centralized error handling
    - Create error handling middleware/decorator for webhook endpoint
    - Catch all exceptions in single handler
    - Log full error details to system_logs:
      - service_name: "email_webhook"
      - log_level: "ERROR" | "WARNING"
      - message: Descriptive event message
      - correlation_id: UUID for request tracing
      - stack_trace: Full traceback
      - metadata: Request context (email_from, status code, etc.)
    - Return generic error message to client (no technical details)
    - Follow pattern from `agent-os/standards/global/error-handling.md`
  - [x] 9.3 Implement specific error logging events
    - Log specific events with appropriate levels:
      - webhook_received: INFO - "Webhook request received"
      - signature_verified: DEBUG - "HMAC-SHA256 signature verified"
      - email_parsed: INFO - "Email parsed successfully"
      - keywords_matched: INFO - "Trading keywords detected: [list]"
      - urls_extracted: INFO - "Portal URLs extracted: [count]"
      - report_created: INFO - "New report created with id: [uuid]"
      - report_duplicate: INFO - "Duplicate email, existing report_id: [uuid]"
      - signature_invalid: WARNING - "Signature verification failed"
      - malformed_payload: WARNING - "Invalid JSON or missing fields"
      - rate_limit_exceeded: WARNING - "Rate limit exceeded"
      - database_error: ERROR - "Database operation failed"
  - [x] 9.4 Implement system_logs insertion
    - Create `src/logging.py` for structured logging
    - Function to write to system_logs table:
      - service_name: Always "email_webhook"
      - log_level: ERROR | WARNING | INFO | DEBUG
      - message: Descriptive event message
      - correlation_id: UUID from request
      - stack_trace: Full Python traceback (if error)
      - metadata: JSONB with context
      - created_at: NOW() set by database
    - Use connection pooling to write logs
    - Handle logging failures gracefully (don't crash webhook)
  - [x] 9.5 Implement input sanitization
    - Validate email addresses (basic format check)
    - Sanitize string fields (no NULL bytes, control characters)
    - Validate JSON structure (Pydantic validation)
    - Use parameterized queries for all database operations
    - Follow pattern from `agent-os/standards/global/validation.md`
  - [x] 9.6 Ensure error handling tests pass
    - Run only the 5-6 tests written in 9.1
    - Verify error handling works for all error types
    - Verify errors logged to system_logs
    - Verify correlation_id included in logs
    - Verify generic error messages (no technical details)
    - Do NOT run entire test suite

**Acceptance Criteria:**
- The 5-6 tests written in 9.1 pass
- All errors logged to system_logs with full context
- Correlation ID included in all logs and responses
- Generic error messages (no stack traces)
- Specific log events for key operations
- Input sanitization prevents injection attacks

---

#### Task Group 10: Response Format & Correlation

**Dependencies:** Task Group 9

- [x] 10.0 Complete response formatting and correlation
  - [x] 10.1 Write 3-4 focused tests for response format
    - Test 201 Created response format
    - Test 202 Accepted response format
    - Test error response format
    - Limit to critical response format behaviors
  - [x] 10.2 Implement standardized response format
    - Success responses (201/202):
      ```json
      {
        "success": true,
        "status": "created" | "accepted",
        "report_id": "[uuid]",
        "correlation_id": "[uuid]",
        "message": "Email processed successfully",
        "timestamp": "[ISO 8601]"
      }
      ```
    - Error responses (400/401/429/500):
      ```json
      {
        "success": false,
        "status": "rejected" | "failed",
        "error": "Generic error message",
        "correlation_id": "[uuid]",
        "timestamp": "[ISO 8601]"
      }
      ```
  - [x] 10.3 Implement correlation_id propagation
    - Generate UUID for each webhook request
    - Include in all logs and database records
    - Return in all responses (success and error)
    - Enable tracing of email through entire pipeline
  - [x] 10.4 Implement ISO 8601 timestamp formatting
    - Format all timestamps as ISO 8601: YYYY-MM-DDTHH:MM:SSZ
    - Use UTC timezone (Z suffix)
    - Format Date header from email as ISO 8601 for storage
  - [x] 10.5 Ensure response format tests pass
    - Run only the 3-4 tests written in 10.1
    - Verify response format matches spec
    - Verify correlation_id present in all responses
    - Verify timestamps in ISO 8601 format
    - Do NOT run entire test suite

**Acceptance Criteria:**
- The 3-4 tests written in 10.1 pass
- All responses follow standardized JSON format
- Correlation ID included in all responses
- Timestamps formatted as ISO 8601
- Success and error responses distinguish properly

---

### Phase 6: Testing, Documentation & Deployment Preparation

**Dependencies:** Task Groups 1-10

#### Task Group 11: Test Review & Gap Analysis

**Dependencies:** Task Groups 1-10

- [x] 11.0 Review existing tests and fill critical gaps
  - [x] 11.1 Review tests from Task Groups 1-10
    - Review 4-6 tests written in Task 1.1 (infrastructure)
    - Review 3-4 tests written in Task 2.1 (database)
    - Review 5-6 tests written in Task 3.1 (security)
    - Review 5-6 tests written in Task 4.1 (parsing)
    - Review 4-5 tests written in Task 5.1 (detection)
    - Review 5-7 tests written in Task 6.1 (extraction)
    - Review 4-5 tests written in Task 7.1 (storage)
    - Review 4-5 tests written in Task 8.1 (rate limiting)
    - Review 5-6 tests written in Task 9.1 (error handling)
    - Review 3-4 tests written in Task 10.1 (response format)
    - Total existing tests: approximately 43-59 focused tests
  - [x] 11.2 Analyze test coverage gaps for THIS feature only
    - Identify critical user workflows lacking test coverage:
      - End-to-end: Email received → validated → stored (happy path)
      - End-to-end: Duplicate email → returns existing report_id
      - End-to-end: No keywords found → returns 202
      - End-to-end: No valid URLs → returns 202 with NULL report_url
      - Integration: Webhook endpoint → database insertion workflow
    - Focus ONLY on gaps related to this spec's feature
    - Do NOT assess entire application test coverage
    - Prioritize end-to-end workflows over unit test gaps
  - [x] 11.3 Write up to 8 additional integration tests maximum
    - Add maximum of 8 new tests to fill identified critical gaps
    - Focus on end-to-end workflows that span multiple phases
    - Test happy path: Valid email with keywords and URLs
    - Test duplicate detection: Same email_message_id twice
    - Test no keywords: Email processed without keyword match
    - Test no URLs: Email processed without valid portal URLs
    - Test rate limit integration: Per-sender and global limits
    - Test error logging: Errors captured in system_logs
    - Do NOT write comprehensive coverage for all scenarios
    - Skip edge cases, performance tests, accessibility unless business-critical
  - [x] 11.4 Run feature-specific tests only
    - Run all tests from Task Groups 1-10 (approximately 43-59 tests)
    - Run up to 8 additional integration tests from Task 11.3
    - Expected total: approximately 51-67 tests
    - Verify critical workflows pass
    - Do NOT run entire application test suite
    - Create test execution summary showing all passed tests

**Acceptance Criteria:**
- All feature-specific tests pass (approximately 51-67 tests)
- Critical end-to-end workflows covered
- No more than 8 additional tests added in gap analysis
- Testing focused exclusively on this spec's feature
- Test execution summary provided

---

#### Task Group 12: Documentation & Deployment Preparation

**Dependencies:** Task Group 11

- [x] 12.0 Complete documentation and deployment setup
  - [x] 12.1 Create service README documentation
    - File: `services/email-webhook/README.md`
    - Include sections:
      - Overview: Brief description of service
      - Architecture: How it fits in pipeline
      - Setup: Installation and configuration steps
      - API: Webhook endpoint documentation (example requests/responses)
      - Testing: How to run tests locally
      - Deployment: Docker/docker-compose configuration
      - Environment Variables: Required configuration
      - Troubleshooting: Common issues and solutions
    - Document webhook payload formats for Mailgun and SendGrid
    - Include example curl requests for testing
  - [x] 12.2 Create Dockerfile for email-webhook service
    - Base image: python:3.12-slim
    - Copy requirements.txt and install dependencies
    - Copy src/ directory
    - Expose port: 8001 (avoid conflict with other services)
    - Set entrypoint: uvicorn src.main:app --host 0.0.0.0 --port 8001
    - Follow pattern from CLAUDE.md microservice structure
  - [x] 12.3 Create requirements.txt
    - FastAPI: Latest stable version
    - uvicorn: ASGI server
    - psycopg2-binary: PostgreSQL driver
    - pydantic: Request validation
    - python-dotenv: Environment configuration
    - Include version pins for reproducibility
  - [x] 12.4 Update docker-compose.yml
    - Add email-webhook service:
      - Container name: email-webhook
      - Image: Build from services/email-webhook/Dockerfile
      - Ports: 8001:8001
      - Environment: Pass DATABASE_URL and other secrets
      - Depends on: postgres service
      - Health check: GET /health endpoint
      - Mount .env file for configuration
    - Network: Same network as postgres service
    - Startup order: postgres first, then email-webhook
  - [x] 12.5 Update .env.example
    - Add email-webhook service variables:
      - WEBHOOK_SIGNATURE_SECRET=[base64 encoded secret]
      - API_KEY_FALLBACK=[optional API key]
      - REPORT_KEYWORDS=[default keywords]
      - TRUSTED_DOMAINS=[default domain/path]
      - RATE_LIMIT_PER_SECOND=1
      - RATE_LIMIT_PER_HOUR=100
      - LOG_LEVEL=INFO
    - Document each variable's purpose
  - [x] 12.6 Update Makefile
    - Add targets for email-webhook service:
      - `make test-email-webhook`: Run tests
      - `make shell-email-webhook`: Interactive shell in container
      - `make logs-email-webhook`: View service logs
      - `make health-email-webhook`: Check service health
  - [x] 12.7 Create API documentation
    - Document POST /webhook/email endpoint:
      - Request format (example JSON payloads)
      - Response format (201, 202, 400, 401, 429, 500)
      - Rate limiting info
      - Authentication requirements
      - Provider-specific headers (X-Signature for Mailgun, etc.)
    - Document GET /health endpoint:
      - Response format
      - Status codes
    - Example: OpenAPI/Swagger spec (FastAPI auto-generates)

**Acceptance Criteria:**
- Comprehensive README documentation created
- Dockerfile works correctly (builds and runs)
- requirements.txt includes all dependencies
- docker-compose.yml updated with email-webhook service
- .env.example includes all new variables
- Makefile targets created for common operations
- API documentation complete and accurate

---

## Execution Order & Dependencies

Recommended implementation sequence:

1. **Phase 1 (Hours 0-2)**: Project Setup & Core Infrastructure
   - Task Group 1: FastAPI scaffold and project structure
   - Task Group 2: Environment configuration and database connectivity
   - Output: Working service with health check and database connection

2. **Phase 2 (Hours 2-6)**: Webhook Endpoint & Request Handling
   - Task Group 3: Webhook endpoint with signature verification
   - Task Group 4: Request parsing and Pydantic validation
   - Output: POST /webhook/email working, requests validated and parsed

3. **Phase 3 (Hours 6-10)**: Email Parsing & Extraction Logic
   - Task Group 5: Keyword-based report detection
   - Task Group 6: URL extraction and portal validation
   - Output: Email content analyzed, keywords matched, URLs extracted

4. **Phase 4 (Hours 10-12)**: Data Storage & Database Integration
   - Task Group 7: PostgreSQL integration and report insertion
   - Output: Reports stored in database, deduplication working

5. **Phase 5 (Hours 12-18)**: Security, Rate Limiting & Error Handling
   - Task Group 8: Rate limiting implementation
   - Task Group 9: Error handling and system logging
   - Task Group 10: Response format and correlation
   - Output: Secure endpoint, rate limiting enforced, errors logged

6. **Phase 6 (Hours 18-20)**: Testing & Deployment Preparation
   - Task Group 11: Test review and gap analysis
   - Task Group 12: Documentation and deployment setup
   - Output: Complete test suite, documentation, ready for deployment

---

## Success Criteria for Complete Implementation

- ✅ Webhook receives and validates email payloads from multiple providers
- ✅ HMAC-SHA256 signature verification works correctly
- ✅ API key fallback authentication implemented
- ✅ Email metadata correctly parsed (headers, subject, body, date)
- ✅ Multipart MIME email bodies handled (plain text and HTML)
- ✅ Keywords detected case-insensitively in subject and body
- ✅ URLs extracted from both plain text and HTML
- ✅ Portal domain/path filtering works (only trusted domains)
- ✅ First valid URL stored in report_url, additional URLs in metadata
- ✅ Email metadata stored in PostgreSQL reports table
- ✅ Deduplication via email_message_id works (UNIQUE constraint)
- ✅ Duplicate emails return existing report_id (202 Accepted, idempotent)
- ✅ Rate limiting enforced (per-sender: 1 req/sec, global: 100 req/hour)
- ✅ All operations logged with correlation_id to system_logs table
- ✅ Error handling is graceful with generic messages (no technical details)
- ✅ JSONB metadata includes: keywords_matched, urls_found_count, provider, etc.
- ✅ All HTTP status codes correct: 201/202/400/401/429/500
- ✅ Rate limit headers in responses (X-RateLimit-Limit, etc.)
- ✅ Health check endpoint verifies database connectivity
- ✅ Service deployable via Docker and docker-compose
- ✅ All feature-specific tests passing (51-67 tests)
- ✅ Comprehensive documentation complete
- ✅ Integration with downstream services ready (N8N orchestration)

---

## Key Implementation Notes

### Reusing Existing Code
- **URL Extraction Pattern**: Reuse `urllib.parse.urlparse()` pattern from refs/scraper.py
- **Database Models**: Leverage existing PostgreSQL schema from 2025-11-25-postgresql-schema-data-persistence spec
- **FastAPI Patterns**: Follow conventions from CLAUDE.md and existing services
- **Error Handling**: Reference agent-os/standards/global/error-handling.md patterns
- **Validation**: Use Pydantic models per agent-os/standards/backend/models.md

### Testing Focus
- Each task group writes 2-8 focused tests (total 43-59 from phases)
- Tests cover only critical behaviors, not exhaustive scenarios
- Integration tests (11.3) focus on end-to-end workflows
- Total test execution: ~51-67 tests, excluding application-wide tests

### Security First
- HMAC-SHA256 signature verification mandatory
- Rate limiting prevents abuse
- Parameterized queries prevent SQL injection
- Generic error messages (no technical details exposed)
- All operations logged for audit trail

### Database Deduplication
- email_message_id as UNIQUE constraint in PostgreSQL
- Duplicate detection at application level
- Idempotent: Duplicate emails return 202 with existing report_id
- No error code or exception for duplicates (expected behavior)

---

## File Structure After Completion

```
services/email-webhook/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, /webhook/email, /health endpoints
│   ├── config.py               # Environment configuration
│   ├── models.py               # Pydantic request/response models
│   ├── parsers.py              # Email header and body parsing
│   ├── detection.py            # Keyword matching logic
│   ├── extractors.py           # URL extraction and validation
│   ├── database.py             # PostgreSQL connection pooling
│   ├── storage.py              # Report insertion and deduplication
│   ├── security.py             # HMAC-SHA256 verification, rate limiting
│   └── logging.py              # System logs insertion
├── tests/
│   ├── __init__.py
│   ├── test_infrastructure.py  # Tests for Task 1.1, 2.1
│   ├── test_security.py        # Tests for Task 3.1
│   ├── test_parsing.py         # Tests for Task 4.1
│   ├── test_detection.py       # Tests for Task 5.1
│   ├── test_extraction.py      # Tests for Task 6.1
│   ├── test_storage.py         # Tests for Task 7.1
│   ├── test_rate_limiting.py   # Tests for Task 8.1
│   ├── test_error_handling.py  # Tests for Task 9.1
│   ├── test_response_format.py # Tests for Task 10.1
│   └── test_integration.py     # Tests for Task 11.3 (gap analysis)
├── Dockerfile
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Standards Compliance

All implementation aligns with agent-os/standards/:
- **backend/api.md**: RESTful design, proper HTTP codes, rate limiting headers
- **backend/models.md**: Pydantic validation, clear field naming, timestamps
- **backend/migrations.md**: Not applicable (schema pre-exists)
- **backend/queries.md**: Parameterized queries, connection pooling
- **global/coding-style.md**: Consistent naming, small focused functions, DRY
- **global/conventions.md**: Clear project structure, env variables, git practices
- **global/error-handling.md**: Specific exception types, generic messages, logging
- **global/validation.md**: Server-side validation, sanitization, business rules
- **testing/test-writing.md**: Minimal tests, focus on core flows, mock dependencies
