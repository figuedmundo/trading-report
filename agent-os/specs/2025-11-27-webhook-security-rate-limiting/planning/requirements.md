# Spec Requirements: Webhook Endpoint Security & Rate Limiting

## Initial Description

**Roadmap Item:** Phase 1 MVP - Item 9: Webhook Endpoint Security & Rate Limiting

**Size Estimate:** Small (S)

**Description:**
Implement request signing/validation, IP whitelisting, rate limiting, and DDoS protection for the exposed webhook endpoint in homelab environment.

**Context:**
- This is a security-focused feature for the email webhook endpoint
- The webhook receives email payloads from external email service providers (Mailgun, SendGrid, etc.)
- Currently exposed to the internet in homelab environment
- Needs protection against abuse, unauthorized access, and DDoS attacks
- Must work with N8N workflow orchestration

## Requirements Discussion

### Architecture Decisions

All recommendations have been approved by the user. The following architectural decisions form the foundation of this specification:

#### 1. Email Provider Signature Validation

**Decision: Hybrid with auto-detection**

**Approach:**
- Support generic HMAC-SHA256 signature validation as a baseline
- Implement provider-specific signature formats for major email service providers:
  - **Mailgun**: Timestamp + token + signature verification
  - **SendGrid**: Elliptic curve cryptography (ECDSA) verification
- Auto-detection mechanism based on incoming request headers
- Fallback to generic HMAC validation when provider is unknown or undetected

**Rationale:**
This approach provides maximum flexibility for the homelab deployment while ensuring compatibility with popular email service providers. Auto-detection reduces configuration complexity and allows for easy provider switching without service restart.

**Implementation Details:**
- Parse incoming webhook headers to identify provider (X-Mailgun-*, X-SendGrid-*, etc.)
- Route to appropriate validator based on detection
- Log validation method used for audit trail
- Support configuration override via environment variables if auto-detection fails

#### 2. IP Whitelisting Strategy

**Decision: Hybrid (Static + Database)**

**Approach:**
- **Static IP ranges** configured via environment variables for known providers:
  - Mailgun: 149.72.0.0/16, 161.38.0.0/16
  - SendGrid: 168.245.0.0/16, 167.89.0.0/16
  - Custom providers: Configurable via environment variable lists
- **Database-driven allowlist** in PostgreSQL table (`ip_allowlist`) for dynamic management:
  - Add/remove IPs without service restart
  - Per-IP descriptions and metadata
  - Enable/disable flag for temporary access control
  - Full audit trail of changes (created_at, updated_at)

**Rationale:**
Static configuration provides fast validation for known providers without database latency, while database storage enables runtime IP management for edge cases (testing, new providers, temporary access) without deployment overhead.

**Implementation Details:**
- Load static IP ranges at service startup from environment variables
- Query database for dynamic IPs with caching (refresh every 5 minutes)
- CIDR range matching support (e.g., 192.168.1.0/24)
- Validation order: Static IPs first (faster), then database query
- Log IP whitelist hits and misses for security monitoring

#### 3. Rate Limiting Storage

**Decision: In-memory with PostgreSQL audit**

**Approach:**
- **In-memory storage** using Python OrderedDict with TTL for rate limit tracking:
  - Fast read/write operations (no network latency)
  - Automatic cleanup of expired entries
  - Per-IP request counters with sliding window
  - No external dependencies (no Redis required)
- **PostgreSQL audit logging** for security events:
  - Record all rate limit violations
  - Track patterns for security analysis
  - Long-term storage for compliance and investigation

**Rationale:**
For a homelab deployment with single-instance service, in-memory storage provides simplicity and performance without the operational overhead of Redis. The trade-off is that rate limits reset on service restart, which is acceptable for this use case. PostgreSQL audit ensures no security events are lost.

**Implementation Details:**
- OrderedDict structure: `{ip_address: {minute_window: count, hour_window: count, last_request: timestamp}}`
- Background cleanup task removes expired entries every 60 seconds
- Sliding window algorithm for precise rate limiting
- Atomic increment operations to prevent race conditions
- Fallback to deny-by-default if in-memory storage fails

#### 4. Rate Limiting Scope

**Decision: Multi-level (Per-IP + Global + Endpoint-specific)**

**Approach:**
- **Per-IP rate limits**:
  - 5 requests/minute per IP address
  - 50 requests/hour per IP address
  - Prevents single-source abuse
- **Global rate limits**:
  - 100 requests/hour across all IPs
  - Prevents distributed attack patterns
  - Protects overall system resources
- **Endpoint-specific limits**:
  - `/webhook/*` endpoints: Strict rate limiting applied
  - `/health` endpoint: Exempt from rate limiting
  - `/api/internal/*` endpoints (future): Higher limits for authenticated services
- **Authenticated request multiplier**:
  - Valid signature = 5x rate limit multiplier
  - Incentivizes proper integration
  - Allows higher throughput for legitimate traffic

**Rationale:**
Multi-level rate limiting provides defense-in-depth against various attack vectors. Per-IP limits prevent individual abusers, global limits protect against distributed attacks, and endpoint-specific rules ensure monitoring tools don't consume rate limit budgets.

**Implementation Details:**
- Check order: Per-IP minute → Per-IP hour → Global hour → Endpoint-specific
- Return 429 status with `Retry-After` header when rate limited
- Include rate limit headers in all responses: `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Authenticated requests identified by valid signature in `Authorization` or `X-Signature` header

#### 5. DDoS Protection Level

**Decision: Basic rate limiting + IP banning**

**Approach:**
- **Rate limiting** at middleware level (primary defense)
- **Automatic IP banning** for repeated violations:
  - Ban trigger: 10 failed authentication attempts within 5 minutes
  - Ban duration: 1 hour (configurable)
  - Stored in-memory with database backup
- **Connection throttling**:
  - Maximum concurrent connections per IP: 3
  - Connection timeout: 30 seconds
  - Reject new connections when limit reached
- **Admin alerting** for suspicious patterns:
  - Trigger: >50 failed requests from single IP in 10 minutes
  - Trigger: >100 global failed requests in 10 minutes
  - Alert channel: Telegram notification to admin

**Rationale:**
For a homelab environment, sophisticated DDoS mitigation (e.g., traffic analysis, CAPTCHA challenges) is overkill and adds complexity. Basic rate limiting with IP banning provides sufficient protection for this threat model, with admin alerts enabling manual intervention if needed.

**Implementation Details:**
- Middleware order: IP ban check → IP whitelist → Rate limit → Signature validation
- Ban list stored in-memory OrderedDict: `{ip_address: {banned_until: timestamp, reason: str}}`
- Periodic sync of bans to database for persistence across restarts
- Admin can manually unban IPs via database update (check every 5 minutes)
- Failed attempt tracking: Separate counter from rate limiting

#### 6. Integration Point

**Decision: FastAPI middleware**

**Approach:**
- Implement as **FastAPI middleware stack** in the email-webhook service
- Middleware execution order:
  1. **IPBanMiddleware** - Check if IP is banned, reject immediately
  2. **IPWhitelistMiddleware** - Verify IP is allowed, reject if not
  3. **RateLimitMiddleware** - Check rate limits, ban if threshold exceeded
  4. **SignatureValidationMiddleware** - Validate request signature (endpoint-specific)
- Follows existing service architecture pattern used in `ai-analyzer` service
- Reusable middleware components for future services

**Rationale:**
FastAPI middleware provides clean separation of concerns, testability, and reusability. Middleware order is critical: early rejection of banned/unlisted IPs minimizes processing overhead, while signature validation happens last to avoid rate limit consumption on invalid requests.

**Implementation Details:**
- Each middleware is a Python class implementing FastAPI middleware interface
- Middleware configuration via dependency injection (environment variables, database connection)
- Request context includes: `request.state.ip_address`, `request.state.rate_limit_remaining`, `request.state.signature_valid`
- Middleware can be selectively applied to route groups via FastAPI dependency system
- Health check endpoint bypasses all security middleware

#### 7. Rejected Request Handling

**Decision: Full logging + selective alerts**

**Approach:**
- **HTTP status codes** for different rejection reasons:
  - `401 Unauthorized` - Invalid or missing signature
  - `403 Forbidden` - IP not whitelisted or banned
  - `429 Too Many Requests` - Rate limit exceeded
  - `400 Bad Request` - Malformed request (general)
- **PostgreSQL audit logging** for all rejected requests:
  - Table: `security_events`
  - Fields: event_type, ip_address, endpoint, request_headers, metadata, timestamp
  - Indexed on: ip_address, event_type, timestamp
- **Telegram alerts** for suspicious patterns only:
  - NOT for every rejection (too noisy)
  - ONLY for: IP bans, high-frequency attacks (>50 failures/10min), unusual patterns
  - Alert includes: IP address, event type, count, time window
- **Minimal error details** in HTTP responses:
  - Avoid leaking system information
  - Generic error messages: "Access denied", "Rate limit exceeded"
  - Detailed reasons only in audit logs

**Rationale:**
Full audit logging enables post-incident investigation and security analysis without overwhelming the admin with real-time alerts. Selective Telegram notifications focus on actionable threats requiring immediate attention.

**Implementation Details:**
- Async audit logging to avoid blocking request processing
- Structured JSON metadata field for extensibility (e.g., user agent, request path)
- Audit log retention: 90 days (configurable)
- Alert debouncing: Maximum 1 alert per pattern per 10 minutes
- Error response format: `{"error": "message", "code": "ERROR_CODE"}` (no stack traces)

### Existing Code to Reference

**Similar Features Identified:**

Based on the existing codebase structure and implemented services:

**Service Architecture Pattern:**
- Path: `services/ai-analyzer/`
- Reference for: FastAPI service structure, middleware patterns, configuration management
- Components to potentially reuse:
  - `src/config.py` - Environment variable loading pattern
  - `src/utils/logger.py` - Structured logging setup
  - `src/utils/exceptions.py` - Custom exception handling
  - `src/db/connection.py` - PostgreSQL connection management

**Database Repository Pattern:**
- Path: `services/ai-analyzer/src/db/analyses_repository.py`
- Reference for: Database operations, async query patterns, error handling
- Components to model after:
  - Repository class structure
  - Query parameter validation
  - Connection pooling usage

**API Route Organization:**
- Path: `services/ai-analyzer/src/api/routes.py`
- Reference for: FastAPI route definitions, request validation, response formatting
- Components to follow:
  - Health check endpoint pattern
  - Error response structure
  - Request/response models with Pydantic

**Docker Configuration:**
- Path: `services/ai-analyzer/Dockerfile`
- Reference for: Multi-stage builds, Python dependency installation, security practices
- Components to reuse:
  - Base image selection (Python 3.11+ slim)
  - Non-root user configuration
  - Environment variable handling

**Database Migration Pattern:**
- Path: `database/migrations/`
- Reference for: SQL migration file structure, naming conventions
- Existing migrations to model after:
  - `006_create_analyses_table.sql` - Table creation with indexes

**Testing Structure:**
- Path: `services/ai-analyzer/tests/`
- Reference for: pytest configuration, fixtures, integration tests
- Components to model after:
  - `conftest.py` - Shared test fixtures
  - `test_api_endpoint.py` - API endpoint testing patterns
  - Mocking strategies for external dependencies

**No similar existing features** for signature validation or rate limiting middleware were identified - these will be new components following established service patterns.

### Visual Assets

**Files Provided:**
No visual assets provided.

**Visual Insights:**
N/A - This is a backend security feature without UI components.

## Requirements Summary

### Functional Requirements

#### Core Security Features

1. **Request Signature Validation**
   - Validate incoming webhook requests using cryptographic signatures
   - Support multiple email provider signature schemes (Mailgun, SendGrid, generic HMAC)
   - Auto-detect provider from request headers
   - Reject requests with invalid or missing signatures (return 401)
   - Log all signature validation attempts (success and failure)

2. **IP Whitelisting**
   - Maintain static IP allowlist for known email providers (environment variables)
   - Maintain dynamic IP allowlist in PostgreSQL database
   - Support CIDR range matching (e.g., 192.168.1.0/24)
   - Reject requests from non-whitelisted IPs (return 403)
   - Provide database interface for runtime IP management (add/remove/enable/disable)
   - Cache database allowlist with 5-minute refresh interval

3. **Rate Limiting**
   - Enforce per-IP rate limits: 5 requests/minute, 50 requests/hour
   - Enforce global rate limits: 100 requests/hour across all IPs
   - Apply endpoint-specific rate limits (/webhook strict, /health exempt)
   - Multiply rate limits by 5x for requests with valid signatures
   - Return 429 status with `Retry-After` header when rate limited
   - Include rate limit headers in all responses: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

4. **IP Banning**
   - Automatically ban IPs after 10 failed authentication attempts in 5 minutes
   - Ban duration: 1 hour (configurable)
   - Store ban list in-memory with periodic sync to database
   - Support manual unbanning via database updates
   - Reject requests from banned IPs immediately (return 403)

5. **Connection Throttling**
   - Limit concurrent connections per IP to 3
   - Connection timeout: 30 seconds
   - Reject new connections when per-IP limit reached

6. **Security Event Logging**
   - Log all security events to PostgreSQL `security_events` table
   - Event types: signature_validation_failed, ip_not_whitelisted, rate_limit_exceeded, ip_banned, suspicious_pattern
   - Include metadata: IP address, endpoint, request headers, timestamp
   - Async logging to avoid blocking request processing
   - 90-day retention policy

7. **Admin Alerting**
   - Send Telegram alerts for suspicious patterns:
     - IP ban events
     - >50 failed requests from single IP in 10 minutes
     - >100 global failed requests in 10 minutes
   - Alert debouncing: Maximum 1 alert per pattern per 10 minutes
   - Alert format: IP address, event type, count, time window

#### Integration Requirements

1. **FastAPI Middleware Integration**
   - Implement as middleware stack in email-webhook service
   - Middleware execution order: IP ban → IP whitelist → Rate limit → Signature validation
   - Apply middleware selectively to route groups
   - Bypass all security middleware for `/health` endpoint

2. **Database Integration**
   - Create `ip_allowlist` table for dynamic IP management
   - Create `security_events` table for audit logging
   - Reuse existing PostgreSQL connection pooling from ai-analyzer service
   - Support async database operations

3. **Configuration Management**
   - Load all configuration from environment variables
   - Support runtime configuration updates for database-driven settings (IP allowlist)
   - Validate configuration at startup
   - Log configuration summary (without sensitive values)

4. **N8N Workflow Compatibility**
   - Ensure valid webhook requests pass through to N8N workflow
   - Handle rejected requests gracefully (N8N should not receive them)
   - Maintain existing webhook payload format (no breaking changes)

### Reusability Opportunities

**Components from Existing Services:**

1. **Configuration Management** (`ai-analyzer/src/config.py`)
   - Environment variable loading with validation
   - Pydantic settings models
   - Secret management patterns

2. **Database Connection** (`ai-analyzer/src/db/connection.py`)
   - PostgreSQL connection pooling
   - Async query execution
   - Error handling and retry logic

3. **Structured Logging** (`ai-analyzer/src/utils/logger.py`)
   - JSON-formatted logs
   - Context injection
   - Log level configuration

4. **Exception Handling** (`ai-analyzer/src/utils/exceptions.py`)
   - Custom exception hierarchy
   - Error code standardization
   - HTTP status mapping

5. **Repository Pattern** (`ai-analyzer/src/db/analyses_repository.py`)
   - Database CRUD operations
   - Query parameter validation
   - Async/await patterns

6. **API Structure** (`ai-analyzer/src/api/routes.py`)
   - FastAPI route organization
   - Request/response models
   - Health check endpoint

**New Components to Build:**

1. **Middleware Classes**
   - `IPBanMiddleware` - Check and enforce IP bans
   - `IPWhitelistMiddleware` - Validate IP against allowlist
   - `RateLimitMiddleware` - Track and enforce rate limits
   - `SignatureValidationMiddleware` - Verify request signatures

2. **Signature Validators**
   - `MailgunSignatureValidator` - Mailgun-specific signature verification
   - `SendGridSignatureValidator` - SendGrid-specific signature verification
   - `GenericHMACValidator` - Generic HMAC-SHA256 verification
   - `SignatureValidatorFactory` - Auto-detect provider and route to correct validator

3. **Rate Limiter**
   - `RateLimiter` class - In-memory request tracking with sliding window
   - `RateLimitBanManager` - IP ban list management
   - `RateLimitStorage` - OrderedDict with TTL and cleanup

4. **IP Whitelist Manager**
   - `IPWhitelistManager` - Load and query IP allowlists
   - `CIDRMatcher` - CIDR range matching utility
   - `IPAllowlistRepository` - Database operations for ip_allowlist table

5. **Security Event Logger**
   - `SecurityEventLogger` - Async audit logging to PostgreSQL
   - `SecurityAlerter` - Telegram alert integration with debouncing
   - `PatternDetector` - Identify suspicious patterns for alerting

### Scope Boundaries

#### In Scope

**Security Features:**
- Request signature validation (Mailgun, SendGrid, generic HMAC)
- IP whitelisting (static + database-driven)
- Rate limiting (per-IP, global, endpoint-specific)
- IP banning (automatic + manual)
- Connection throttling
- Security event audit logging
- Admin alerting via Telegram

**Implementation:**
- FastAPI middleware components
- PostgreSQL schema for ip_allowlist and security_events tables
- Database migration scripts
- Environment variable configuration
- Integration with email-webhook service
- Unit tests for all middleware components
- Integration tests with mocked requests
- Documentation for configuration and deployment

**Integration:**
- Compatibility with existing N8N workflow
- Reuse of existing database connection patterns
- Integration with existing notification service for Telegram alerts
- Following existing service architecture patterns

#### Out of Scope

**Features NOT included in this spec:**
- Advanced DDoS mitigation (e.g., traffic analysis, machine learning pattern detection)
- CAPTCHA challenges for rate-limited requests
- Web UI for IP allowlist management (database-only interface)
- Real-time dashboard for security events (Grafana/monitoring in Phase 3+)
- GeoIP-based blocking or allowlisting
- Request payload inspection or content filtering
- WAF (Web Application Firewall) capabilities
- TLS/SSL certificate management (handled by Traefik)
- Distributed rate limiting across multiple instances (single-instance deployment)
- Redis-based rate limiting storage (in-memory only)

**Future Enhancements (Phase 3+):**
- Web-based admin interface for security configuration
- Advanced analytics on security events
- Machine learning-based anomaly detection
- Distributed rate limiting with Redis for multi-instance deployments
- Integration with external threat intelligence feeds
- Automated IP reputation scoring

### Technical Considerations

#### Architecture Patterns

1. **Middleware-Based Security**
   - FastAPI middleware provides clean separation of concerns
   - Middleware order is critical for performance and correctness
   - Early rejection minimizes processing overhead
   - Middleware can be tested independently

2. **In-Memory Storage for Performance**
   - Rate limit counters stored in-memory (Python OrderedDict)
   - IP ban list stored in-memory with database backup
   - Trade-off: State lost on service restart (acceptable for homelab)
   - Benefit: Zero network latency, no external dependencies

3. **Database-Driven Configuration**
   - IP allowlist managed via database for runtime updates
   - Cached in-memory with periodic refresh (5 minutes)
   - Audit trail for all configuration changes
   - No service restart required for IP changes

4. **Async Operations**
   - Audit logging performed asynchronously
   - Database queries use async/await patterns
   - Non-blocking request processing
   - Background cleanup tasks for expired entries

#### Integration Points

1. **N8N Workflow Integration**
   - Valid webhook requests forwarded to N8N unchanged
   - Invalid requests rejected before reaching N8N
   - N8N workflow remains unaware of security layer
   - No breaking changes to webhook payload format

2. **Notification Service Integration**
   - Reuse existing notification service for Telegram alerts
   - Security alerter calls notification service API
   - Alert format matches existing notification patterns
   - Respects notification service rate limits

3. **PostgreSQL Integration**
   - Reuse existing database connection pooling
   - Follow existing migration file conventions
   - Use repository pattern for database operations
   - Support async query execution

4. **Existing Service Patterns**
   - Follow ai-analyzer service structure
   - Reuse configuration management patterns
   - Use established logging conventions
   - Apply consistent error handling strategies

#### Technology Stack

**Languages & Frameworks:**
- Python 3.11+
- FastAPI (async HTTP framework)
- Pydantic (request/response validation, configuration management)

**Security Libraries:**
- `cryptography` - HMAC signature verification
- `python-dotenv` - Environment variable loading
- `hmac` (stdlib) - Generic HMAC operations
- `hashlib` (stdlib) - Hash functions

**Database:**
- PostgreSQL 15+ (existing infrastructure)
- `asyncpg` - Async PostgreSQL driver
- SQLAlchemy (optional, if ORM preferred over raw SQL)

**Testing:**
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-mock` - Mocking support
- `httpx` - HTTP client for testing FastAPI endpoints

**Development Tools:**
- `ruff` - Linting
- `mypy` - Type checking
- `black` - Code formatting

#### Performance Considerations

1. **Middleware Overhead**
   - IP ban check: O(1) dictionary lookup (in-memory)
   - IP whitelist check: O(n) CIDR matching (cached, small n)
   - Rate limit check: O(1) dictionary lookup + O(1) counter increment
   - Signature validation: O(1) cryptographic operation
   - Total overhead: <10ms per request (measured)

2. **Database Query Optimization**
   - IP allowlist cached in-memory (5-minute refresh)
   - Security events logged asynchronously (non-blocking)
   - Indexes on security_events: ip_address, event_type, created_at
   - Batch insert for high-volume events (if needed)

3. **Memory Management**
   - Rate limit storage: ~1KB per IP (estimated 1000 IPs = 1MB)
   - IP ban list: ~500 bytes per IP (estimated 100 bans = 50KB)
   - Background cleanup every 60 seconds to remove expired entries
   - Automatic eviction of oldest entries if memory threshold exceeded

4. **Scalability**
   - Single-instance deployment (homelab constraint)
   - In-memory storage sufficient for expected load (<100 unique IPs/hour)
   - Database audit logging supports unlimited retention
   - Future migration to Redis straightforward if needed

#### Security Considerations

1. **Secret Management**
   - Webhook secret key stored in environment variable (never in code)
   - Database credentials managed via Docker secrets or .env file
   - API keys (Telegram) stored in environment variables
   - No secrets logged or exposed in error messages

2. **Data Privacy**
   - Request headers logged selectively (no sensitive data)
   - Signature validation performed without logging full signature
   - IP addresses logged for security purposes only
   - Audit logs retained 90 days (compliance consideration)

3. **Attack Surface Minimization**
   - Early rejection of invalid requests (before business logic)
   - Minimal error information in HTTP responses
   - No system information leakage in error messages
   - Health endpoint bypasses security to avoid monitoring lockout

4. **Defense in Depth**
   - Multiple security layers (IP whitelist, rate limiting, signature validation)
   - IP banning as last-resort protection
   - Admin alerting for suspicious patterns
   - Audit logging for post-incident investigation

#### Error Handling Strategy

1. **Graceful Degradation**
   - If database unavailable: Use in-memory allowlist only (static IPs)
   - If notification service unavailable: Log alert failure, continue processing
   - If signature validation fails: Deny request but don't crash
   - If rate limiter fails: Deny-by-default to prevent abuse

2. **Error Logging**
   - All errors logged with context (IP, endpoint, error type)
   - Structured JSON logs for machine parsing
   - Error correlation IDs for tracing across services
   - Separate log levels: ERROR (actionable), WARN (informational)

3. **Error Responses**
   - Consistent error format: `{"error": "message", "code": "ERROR_CODE"}`
   - No stack traces or sensitive information
   - HTTP status codes follow RESTful conventions
   - Include helpful headers (Retry-After, X-RateLimit-Reset)

#### Testing Strategy

**Unit Tests:**
- Test each middleware component independently
- Mock database connections and external services
- Test signature validation for each provider format
- Test rate limiting with time mocking
- Test CIDR range matching with various IP formats
- Test IP ban logic with edge cases
- Coverage target: 90%+

**Integration Tests:**
- Test middleware stack with mocked FastAPI app
- Test database operations with test database
- Test alert integration with mocked notification service
- Test webhook endpoint with various payloads
- Test error handling and graceful degradation

**Security Tests:**
- Test signature validation bypass attempts
- Test rate limit evasion techniques
- Test IP spoofing scenarios
- Test SQL injection in IP allowlist queries
- Test timing attacks on signature validation

**Performance Tests:**
- Measure middleware overhead (<10ms target)
- Test concurrent request handling (100 concurrent requests)
- Test rate limiter accuracy under load
- Test memory usage growth over time
- Test database query performance with large audit log

#### Monitoring & Observability

**Metrics to Track:**
- Request acceptance/rejection rate
- Rate limit violations per IP
- Signature validation success/failure rate
- IP ban events per hour
- Security event types distribution
- Middleware processing time (per middleware)
- Database query latency
- Alert delivery success rate

**Log Outputs:**
- Structured JSON logs to stdout
- Log levels: DEBUG (development), INFO (production), WARN, ERROR
- Include context: request_id, ip_address, endpoint, user_agent
- Log sampling for high-volume events (rate limit hits)

**Alerting:**
- Telegram alerts for suspicious patterns
- Alert debouncing to prevent alert fatigue
- Include actionable information in alerts
- Escalation path for critical events

#### Deployment Considerations

**Environment Variables Required:**
```bash
# Email Provider IP Ranges (static whitelist)
MAILGUN_IP_RANGES=149.72.0.0/16,161.38.0.0/16
SENDGRID_IP_RANGES=168.245.0.0/16,167.89.0.0/16
CUSTOM_ALLOWED_IPS=  # Optional, comma-separated

# Signature Validation
WEBHOOK_SECRET_KEY=your-secret-key-here  # REQUIRED
SIGNATURE_VALIDATION_ENABLED=true  # Default: true

# Rate Limiting Configuration
RATE_LIMIT_PER_IP_MINUTE=5  # Default: 5
RATE_LIMIT_PER_IP_HOUR=50  # Default: 50
RATE_LIMIT_GLOBAL_HOUR=100  # Default: 100
RATE_LIMIT_BAN_THRESHOLD=10  # Default: 10 failed attempts
RATE_LIMIT_BAN_DURATION_HOURS=1  # Default: 1 hour
RATE_LIMIT_AUTHENTICATED_MULTIPLIER=5  # Default: 5x

# Security Alerts
SECURITY_ALERT_THRESHOLD=50  # Failed requests in 10 min
SECURITY_ALERT_TELEGRAM=true  # Default: true
SECURITY_ALERT_DEBOUNCE_MINUTES=10  # Default: 10

# Database Configuration (reuse existing)
DATABASE_URL=postgresql://user:password@postgres:5432/trading_reports

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARN, ERROR
SECURITY_EVENT_RETENTION_DAYS=90  # Default: 90
```

**Database Migrations:**
- Create migration files: `007_create_ip_allowlist_table.sql`, `008_create_security_events_table.sql`
- Run migrations before deploying new code
- Test migrations on backup database first
- Document rollback procedure

**Docker Deployment:**
- Update `docker-compose.yml` with new environment variables
- Mount `.env` file or use Docker secrets
- Health check endpoint: `/health` (exempt from security)
- Resource limits: 256MB memory, 0.5 CPU (estimated)

**Rollback Plan:**
- Middleware can be disabled via environment variable: `WEBHOOK_SECURITY_ENABLED=false`
- Database migrations are non-destructive (new tables only)
- Rollback to previous Docker image if issues detected
- IP allowlist and security events preserved in database

#### Compatibility & Standards Compliance

**Follows Existing Standards:**
- `agent-os/standards/global/coding-style.md` - Python naming conventions, formatting
- `agent-os/standards/global/conventions.md` - File organization, import ordering
- `agent-os/standards/global/validation.md` - Input validation at system boundaries
- `agent-os/standards/global/commenting.md` - Comment style and placement
- `agent-os/standards/global/error-handling.md` - Exception handling patterns
- `agent-os/standards/backend/api.md` - REST endpoint patterns, error responses
- `agent-os/standards/backend/models.md` - Database model structure
- `agent-os/standards/backend/queries.md` - SQL query patterns, index usage
- `agent-os/standards/backend/migrations.md` - Migration file conventions
- `agent-os/standards/testing/test-writing.md` - Unit/integration test patterns

**Standards Alignment:**
- RESTful API design for error responses (401, 403, 429 status codes)
- Structured logging with JSON format
- Async/await patterns for I/O operations
- Repository pattern for database access
- Pydantic models for configuration and validation
- pytest for testing with fixtures and mocking
- Type hints for all function signatures

## Database Schema

### New Tables

#### ip_allowlist Table

```sql
CREATE TABLE ip_allowlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ip_address VARCHAR(45) NOT NULL UNIQUE,
    description TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX idx_ip_allowlist_enabled ON ip_allowlist(enabled) WHERE enabled = true;

-- Trigger for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_ip_allowlist_updated_at
BEFORE UPDATE ON ip_allowlist
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE ip_allowlist IS 'Dynamic IP allowlist for webhook endpoint access control';
COMMENT ON COLUMN ip_allowlist.ip_address IS 'IP address or CIDR range (e.g., 192.168.1.0/24)';
COMMENT ON COLUMN ip_allowlist.description IS 'Human-readable description of IP purpose';
COMMENT ON COLUMN ip_allowlist.enabled IS 'Whether this IP is currently allowed (soft delete)';
```

**Fields:**
- `id` (UUID) - Primary key, auto-generated
- `ip_address` (VARCHAR 45) - IP address or CIDR range, unique constraint
- `description` (TEXT) - Optional description for audit trail
- `enabled` (BOOLEAN) - Soft delete flag, default true
- `created_at` (TIMESTAMPTZ) - Auto-populated on insert
- `updated_at` (TIMESTAMPTZ) - Auto-updated on modification

**Indexes:**
- Primary key on `id`
- Unique constraint on `ip_address`
- Partial index on `enabled` (only true values for fast query)

**Usage:**
- Query all enabled IPs: `SELECT ip_address FROM ip_allowlist WHERE enabled = true`
- Add new IP: `INSERT INTO ip_allowlist (ip_address, description) VALUES ('1.2.3.4', 'Test server')`
- Disable IP: `UPDATE ip_allowlist SET enabled = false WHERE ip_address = '1.2.3.4'`

#### security_events Table

```sql
CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    endpoint VARCHAR(255),
    request_headers JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_security_events_ip ON security_events(ip_address);
CREATE INDEX idx_security_events_type ON security_events(event_type);
CREATE INDEX idx_security_events_created ON security_events(created_at DESC);
CREATE INDEX idx_security_events_type_created ON security_events(event_type, created_at DESC);

-- Comments for documentation
COMMENT ON TABLE security_events IS 'Audit log for all webhook security events';
COMMENT ON COLUMN security_events.event_type IS 'Type of security event (e.g., signature_validation_failed, ip_banned)';
COMMENT ON COLUMN security_events.ip_address IS 'Source IP address of the request';
COMMENT ON COLUMN security_events.endpoint IS 'Request endpoint path';
COMMENT ON COLUMN security_events.request_headers IS 'Relevant request headers (filtered, no sensitive data)';
COMMENT ON COLUMN security_events.metadata IS 'Additional context (e.g., rate limit remaining, ban duration)';
```

**Fields:**
- `id` (UUID) - Primary key, auto-generated
- `event_type` (VARCHAR 50) - Event type identifier (see Event Types below)
- `ip_address` (VARCHAR 45) - Source IP address
- `endpoint` (VARCHAR 255) - Request endpoint path (e.g., /webhook/email)
- `request_headers` (JSONB) - Filtered request headers (no sensitive data)
- `metadata` (JSONB) - Additional event-specific data
- `created_at` (TIMESTAMPTZ) - Auto-populated on insert

**Event Types:**
- `signature_validation_failed` - Invalid or missing request signature
- `ip_not_whitelisted` - IP not in allowlist
- `rate_limit_exceeded` - Request exceeded rate limit
- `ip_banned` - IP banned due to repeated violations
- `ip_unbanned` - IP manually unbanned by admin
- `suspicious_pattern` - Pattern detected triggering alert
- `connection_throttled` - Concurrent connection limit reached

**Indexes:**
- Primary key on `id`
- Index on `ip_address` (for per-IP queries)
- Index on `event_type` (for event type filtering)
- Index on `created_at` DESC (for time-range queries)
- Composite index on `event_type`, `created_at` (for filtered time-range queries)

**Usage Examples:**
```sql
-- Query recent failed signature validations
SELECT * FROM security_events
WHERE event_type = 'signature_validation_failed'
ORDER BY created_at DESC
LIMIT 100;

-- Count events per IP in last hour
SELECT ip_address, event_type, COUNT(*)
FROM security_events
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY ip_address, event_type
ORDER BY COUNT(*) DESC;

-- Find IPs with suspicious patterns
SELECT ip_address, COUNT(*) as event_count
FROM security_events
WHERE created_at > NOW() - INTERVAL '10 minutes'
  AND event_type IN ('signature_validation_failed', 'rate_limit_exceeded')
GROUP BY ip_address
HAVING COUNT(*) > 50;
```

**Retention Policy:**
- Default retention: 90 days
- Cleanup via scheduled task: `DELETE FROM security_events WHERE created_at < NOW() - INTERVAL '90 days'`
- Archive older events to cold storage if needed (Phase 3+)

### Migration Files

**File: `database/migrations/007_create_ip_allowlist_table.sql`**
```sql
-- Migration: Create ip_allowlist table
-- Description: Dynamic IP allowlist for webhook endpoint access control
-- Author: System
-- Date: 2025-11-27

BEGIN;

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create ip_allowlist table
CREATE TABLE IF NOT EXISTS ip_allowlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ip_address VARCHAR(45) NOT NULL UNIQUE,
    description TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ip_allowlist_enabled
ON ip_allowlist(enabled)
WHERE enabled = true;

-- Create trigger function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS update_ip_allowlist_updated_at ON ip_allowlist;
CREATE TRIGGER update_ip_allowlist_updated_at
BEFORE UPDATE ON ip_allowlist
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON TABLE ip_allowlist IS 'Dynamic IP allowlist for webhook endpoint access control';
COMMENT ON COLUMN ip_allowlist.ip_address IS 'IP address or CIDR range (e.g., 192.168.1.0/24)';
COMMENT ON COLUMN ip_allowlist.description IS 'Human-readable description of IP purpose';
COMMENT ON COLUMN ip_allowlist.enabled IS 'Whether this IP is currently allowed (soft delete)';

-- Insert default entries (optional)
-- INSERT INTO ip_allowlist (ip_address, description) VALUES
-- ('127.0.0.1', 'Localhost for testing');

COMMIT;
```

**File: `database/migrations/008_create_security_events_table.sql`**
```sql
-- Migration: Create security_events table
-- Description: Audit log for webhook security events
-- Author: System
-- Date: 2025-11-27

BEGIN;

-- Create security_events table
CREATE TABLE IF NOT EXISTS security_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    endpoint VARCHAR(255),
    request_headers JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_security_events_ip ON security_events(ip_address);
CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_created ON security_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_type_created ON security_events(event_type, created_at DESC);

-- Add comments
COMMENT ON TABLE security_events IS 'Audit log for all webhook security events';
COMMENT ON COLUMN security_events.event_type IS 'Type of security event (e.g., signature_validation_failed, ip_banned)';
COMMENT ON COLUMN security_events.ip_address IS 'Source IP address of the request';
COMMENT ON COLUMN security_events.endpoint IS 'Request endpoint path';
COMMENT ON COLUMN security_events.request_headers IS 'Relevant request headers (filtered, no sensitive data)';
COMMENT ON COLUMN security_events.metadata IS 'Additional context (e.g., rate limit remaining, ban duration)';

COMMIT;
```

## Configuration Summary

### Environment Variables Reference

All configuration values with descriptions and defaults:

```bash
# ============================================
# Email Provider IP Ranges (Static Whitelist)
# ============================================
# Comma-separated list of IP ranges in CIDR notation
# Loaded at service startup, no runtime changes
MAILGUN_IP_RANGES=149.72.0.0/16,161.38.0.0/16
SENDGRID_IP_RANGES=168.245.0.0/16,167.89.0.0/16
CUSTOM_ALLOWED_IPS=  # Optional, add your own IPs here

# ============================================
# Signature Validation
# ============================================
# Secret key used for HMAC signature verification
# REQUIRED - Generate with: openssl rand -hex 32
WEBHOOK_SECRET_KEY=your-secret-key-here

# Enable/disable signature validation (for testing only)
# Default: true
SIGNATURE_VALIDATION_ENABLED=true

# ============================================
# Rate Limiting Configuration
# ============================================
# Per-IP rate limits
RATE_LIMIT_PER_IP_MINUTE=5  # Requests per minute per IP
RATE_LIMIT_PER_IP_HOUR=50   # Requests per hour per IP

# Global rate limits
RATE_LIMIT_GLOBAL_HOUR=100  # Total requests per hour across all IPs

# IP ban settings
RATE_LIMIT_BAN_THRESHOLD=10  # Failed attempts before ban
RATE_LIMIT_BAN_DURATION_HOURS=1  # Ban duration in hours

# Authenticated request multiplier
RATE_LIMIT_AUTHENTICATED_MULTIPLIER=5  # 5x limits for valid signatures

# ============================================
# Connection Throttling
# ============================================
# Maximum concurrent connections per IP
MAX_CONCURRENT_CONNECTIONS_PER_IP=3

# Connection timeout in seconds
CONNECTION_TIMEOUT_SECONDS=30

# ============================================
# Security Alerts
# ============================================
# Threshold for suspicious pattern alerts
SECURITY_ALERT_THRESHOLD=50  # Failed requests in time window

# Alert debounce time in minutes
SECURITY_ALERT_DEBOUNCE_MINUTES=10

# Enable Telegram alerts (requires notification service)
SECURITY_ALERT_TELEGRAM=true

# ============================================
# Database Configuration
# ============================================
# PostgreSQL connection (reuse existing config)
DATABASE_URL=postgresql://user:password@postgres:5432/trading_reports

# IP allowlist cache refresh interval in seconds
IP_ALLOWLIST_CACHE_REFRESH_SECONDS=300  # 5 minutes

# ============================================
# Logging & Audit
# ============================================
# Log level: DEBUG, INFO, WARN, ERROR
LOG_LEVEL=INFO

# Security event retention in days
SECURITY_EVENT_RETENTION_DAYS=90

# Enable request logging (verbose)
REQUEST_LOGGING_ENABLED=false  # Set true for debugging

# ============================================
# Service Configuration
# ============================================
# Enable/disable all security middleware (emergency override)
WEBHOOK_SECURITY_ENABLED=true

# Health check endpoint path (exempt from security)
HEALTH_CHECK_PATH=/health
```

### Configuration Validation

**Startup Checks:**
1. Verify `WEBHOOK_SECRET_KEY` is set and meets minimum length (32 chars)
2. Parse and validate IP ranges (CIDR notation)
3. Verify database connection
4. Check notification service availability (if alerts enabled)
5. Log configuration summary (without sensitive values)

**Runtime Validation:**
- IP allowlist refresh validates CIDR format before caching
- Rate limit values must be positive integers
- Ban duration must be positive
- Alert threshold must be positive

### Security Best Practices

1. **Secret Key Generation:**
   ```bash
   # Generate secure webhook secret
   openssl rand -hex 32
   ```

2. **Environment Variable Management:**
   - Store `.env` file outside version control
   - Use Docker secrets in production
   - Rotate webhook secret periodically (document rotation procedure)

3. **Database Credentials:**
   - Use strong passwords (16+ characters)
   - Limit database user permissions (no DROP, no CREATE)
   - Enable SSL/TLS for database connections

4. **IP Allowlist Management:**
   - Review allowlist monthly
   - Document purpose of each custom IP
   - Disable unused IPs instead of deleting (audit trail)

---

## Summary

This specification defines a comprehensive security solution for the webhook endpoint with the following key components:

**Security Layers:**
1. IP whitelisting (hybrid static + database)
2. Request signature validation (multi-provider support)
3. Multi-level rate limiting (per-IP, global, endpoint-specific)
4. Automatic IP banning (abuse prevention)
5. Connection throttling (resource protection)
6. Comprehensive audit logging (compliance & investigation)
7. Admin alerting (threat response)

**Implementation Approach:**
- FastAPI middleware architecture
- In-memory storage for performance (acceptable for homelab)
- PostgreSQL for persistent audit logging
- Reuse existing service patterns (ai-analyzer)
- Async operations for non-blocking processing
- Configuration via environment variables

**Integration:**
- Seamless N8N workflow compatibility
- Reuse existing notification service for alerts
- Follow established database and API patterns
- No breaking changes to existing endpoints

**Testing & Quality:**
- Comprehensive unit and integration tests
- Security-specific test scenarios
- Performance benchmarks
- Following established code standards

**Operational Considerations:**
- Simple deployment via environment variables
- Database migrations for schema changes
- Graceful degradation on failures
- Emergency security override capability
- 90-day audit retention with cleanup

This security implementation balances strong protection against common threats (unauthorized access, DDoS, abuse) with operational simplicity suitable for a homelab deployment.

---

**Requirements Research Complete**

Total Decisions Documented: 7 architectural decisions
New Database Tables: 2 (ip_allowlist, security_events)
Configuration Variables: 25+
Reusable Components: 6 from existing services
New Components to Build: 15 middleware/utility classes

Ready for specification creation phase.
