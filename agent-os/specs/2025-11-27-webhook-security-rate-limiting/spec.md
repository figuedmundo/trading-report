# Specification: Webhook Endpoint Security & Rate Limiting

## Goal
Implement multi-layered security protection for the exposed webhook endpoint including signature validation, IP whitelisting, rate limiting, and automatic IP banning to defend against unauthorized access and DDoS attacks in a homelab environment.

## User Stories
- As a system administrator, I want webhook requests automatically validated with cryptographic signatures so that only legitimate email service providers can trigger workflows
- As a system administrator, I want automatic rate limiting and IP banning so that the webhook endpoint remains available even under attack conditions

## Specific Requirements

### Request Signature Validation
- Implement hybrid signature validation supporting Mailgun (timestamp + token + HMAC), SendGrid (elliptic curve), and generic HMAC-SHA256 fallback
- Auto-detect email provider from incoming request headers (X-Mailgun-*, X-SendGrid-*, etc.) and route to appropriate validator
- Reject requests with invalid or missing signatures using HTTP 401 status with minimal error details to prevent information leakage
- Apply signature validation as the final middleware layer (after IP whitelist and rate limiting) to optimize processing order
- Store webhook secret key in environment variable (WEBHOOK_SECRET_KEY) and validate minimum 32-character length at startup
- Support optional signature validation bypass via SIGNATURE_VALIDATION_ENABLED=false for local testing only
- Log all signature validation attempts (success and failure) to security_events table with provider type metadata
- Multiply rate limits by 5x for requests with valid signatures to incentivize proper integration

### IP Whitelisting with Hybrid Storage
- Load static IP ranges from environment variables at startup (MAILGUN_IP_RANGES, SENDGRID_IP_RANGES, CUSTOM_ALLOWED_IPS) using comma-separated CIDR notation
- Query dynamic IP allowlist from PostgreSQL ip_allowlist table with in-memory caching and 5-minute refresh interval to enable runtime updates
- Support CIDR range matching for both static and dynamic IPs (e.g., 192.168.1.0/24, 149.72.0.0/16)
- Validate IP addresses using a two-tier approach: check static ranges first (faster O(n) scan), then query cached database allowlist
- Reject non-whitelisted IPs immediately with HTTP 403 status before processing request further
- Provide database interface for runtime IP management (INSERT, UPDATE enabled flag, soft delete pattern) without service restart
- Log all IP whitelist misses to security_events table with ip_not_whitelisted event type
- Include /health endpoint exemption from IP whitelisting to prevent monitoring lockout

### Multi-Level Rate Limiting
- Enforce per-IP rate limits using sliding window: 5 requests/minute and 50 requests/hour stored in in-memory OrderedDict with TTL
- Enforce global rate limit of 100 requests/hour across all IPs to protect against distributed attacks
- Apply endpoint-specific rules: strict limits on /webhook/* paths, exempt /health from all rate limiting
- Return HTTP 429 with Retry-After header (seconds until limit reset) and include X-RateLimit-Remaining and X-RateLimit-Reset headers in all responses
- Track request counters per IP using structure: {ip_address: {minute_window: count, hour_window: count, last_request: timestamp}}
- Implement background cleanup task running every 60 seconds to remove expired rate limit entries and prevent memory growth
- Log rate limit violations to security_events with metadata including current limit, remaining quota, and reset timestamp
- Support configurable rate limit values via environment variables (RATE_LIMIT_PER_IP_MINUTE, RATE_LIMIT_PER_IP_HOUR, RATE_LIMIT_GLOBAL_HOUR)

### Automatic IP Banning
- Track failed authentication attempts per IP (signature validation failures, IP whitelist misses) in separate counter from rate limiting
- Automatically ban IP addresses after 10 failed attempts within 5-minute window with configurable threshold (RATE_LIMIT_BAN_THRESHOLD)
- Store ban list in-memory OrderedDict with structure: {ip_address: {banned_until: timestamp, reason: str, attempt_count: int}}
- Enforce 1-hour ban duration (configurable via RATE_LIMIT_BAN_DURATION_HOURS) with automatic expiry and periodic cleanup
- Reject banned IPs immediately at first middleware layer with HTTP 403 and minimal error message
- Sync ban list to database every 5 minutes for persistence across service restarts
- Support manual unbanning via database UPDATE on ip_bans table with next cache refresh picking up changes
- Log all ban events (IP banned, IP unbanned, ban expired) to security_events table with full context including attempt count and ban duration

### Security Event Audit Logging
- Create PostgreSQL security_events table with fields: id (UUID), event_type (VARCHAR 50), ip_address (VARCHAR 45), endpoint (VARCHAR 255), request_headers (JSONB), metadata (JSONB), created_at (TIMESTAMPTZ)
- Implement async audit logging to avoid blocking request processing using background tasks
- Log event types: signature_validation_failed, ip_not_whitelisted, rate_limit_exceeded, ip_banned, ip_unbanned, suspicious_pattern, connection_throttled
- Filter request headers before logging to exclude sensitive data (Authorization, X-Signature values, only log header names)
- Store extensible metadata in JSONB field including rate_limit_remaining, ban_duration, provider_detected, user_agent_hash
- Create indexes on ip_address, event_type, created_at DESC, and composite (event_type, created_at) for query performance
- Implement 90-day retention policy with scheduled cleanup task (configurable via SECURITY_EVENT_RETENTION_DAYS)
- Support batch inserts for high-volume events to optimize database performance under attack conditions

### Admin Alerting System
- Send Telegram alerts only for actionable threats: IP ban events, >50 failed requests from single IP in 10 minutes, >100 global failures in 10 minutes
- Implement alert debouncing with maximum 1 alert per pattern per 10 minutes (SECURITY_ALERT_DEBOUNCE_MINUTES) to prevent notification spam
- Integrate with existing notification service API by calling its Telegram endpoint with formatted alert message
- Include alert details: IP address, event type, event count, time window, timestamp, and recommended action
- Maintain in-memory alert tracking to enforce debounce windows using OrderedDict: {alert_key: last_sent_timestamp}
- Support alert enable/disable via SECURITY_ALERT_TELEGRAM environment variable
- Log alert delivery attempts (success and failure) to application logs with alert metadata
- Implement graceful degradation if notification service unavailable (log error but continue processing requests)

## Existing Code to Leverage

### Configuration Management Pattern (ai-analyzer/src/config.py)
- Reuse Config class pattern with environment variable loading via os.getenv() with type conversion and defaults
- Apply validate_config() pattern to check required fields at startup (WEBHOOK_SECRET_KEY, DATABASE_URL)
- Use python-dotenv for .env file loading in development environment
- Implement get_config() singleton pattern for centralized configuration access
- Log configuration summary at startup without exposing sensitive values (mask secrets in logs)

### Database Connection Pooling (ai-analyzer/src/db/connection.py)
- Reuse asyncpg pool initialization with init_db_pool() function setting min_size=5, max_size=20, command_timeout=10
- Implement get_db_connection() context manager pattern for safe connection acquisition and release
- Apply global _pool singleton pattern to share connections across middleware components
- Use close_db_pool() in lifespan shutdown handler to gracefully close connections
- Handle DatabaseError exceptions with context dict for error tracking

### Structured JSON Logging (ai-analyzer/src/utils/logger.py)
- Extend JSONFormatter class to add security-specific fields: ip_address, event_type, endpoint, request_id
- Reuse get_logger(name) function for consistent logger creation across middleware
- Maintain structured log format with timestamp, level, service, message, and extra fields
- Configure log level via LOG_LEVEL environment variable (DEBUG, INFO, WARN, ERROR)
- Output logs to stdout for Docker container log aggregation

### Custom Exception Hierarchy (ai-analyzer/src/utils/exceptions.py)
- Create SecurityError base exception extending AnalysisError pattern with message, error_code, context fields
- Define specific exceptions: SignatureValidationError, IPNotWhitelistedError, RateLimitExceededError, IPBannedError
- Include error_code field for machine-readable error classification
- Store context dict for error details used in logging but not exposed to clients
- Map exception types to HTTP status codes in middleware error handlers

### FastAPI Middleware Structure (ai-analyzer/src/main.py)
- Follow app.add_middleware() pattern with explicit ordering: IPBanMiddleware, IPWhitelistMiddleware, RateLimitMiddleware, SignatureValidationMiddleware
- Implement @asynccontextmanager lifespan pattern for startup (initialize pools, load IP allowlist) and shutdown (close pools, cleanup tasks)
- Use FastAPI dependency injection for shared resources (database pool, rate limiter instance, IP allowlist manager)
- Apply router.include_router() pattern for health check endpoint with security middleware bypass
- Add CORS middleware configuration for service-to-service communication

### Database Migration Pattern (database/migrations/006_create_analyses_table.sql)
- Follow migration file naming convention: 007_create_ip_allowlist_table.sql, 008_create_security_events_table.sql
- Use IF NOT EXISTS checks for idempotent migrations
- Create indexes inline with CREATE INDEX IF NOT EXISTS for query optimization
- Add COMMENT ON TABLE and COMMENT ON COLUMN for schema documentation
- Wrap migrations in BEGIN/COMMIT transaction blocks for atomicity

## Out of Scope
- Advanced DDoS mitigation using machine learning pattern detection or traffic analysis algorithms
- CAPTCHA challenge integration for rate-limited requests (no user-facing interface)
- Web-based admin UI for IP allowlist management (database-only interface in Phase 1)
- Real-time security dashboard or metrics visualization (Grafana integration deferred to Phase 3+)
- GeoIP-based blocking or allowlisting using MaxMind or similar databases
- Request payload content inspection, XSS filtering, or SQL injection detection (WAF capabilities)
- TLS/SSL certificate management or renewal automation (handled by Traefik reverse proxy)
- Distributed rate limiting with Redis for multi-instance deployments (single-instance homelab only)
- OAuth2 or JWT authentication for webhook endpoints (signature validation sufficient)
- Automated IP reputation scoring using external threat intelligence feeds
