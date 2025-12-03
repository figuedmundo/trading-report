# Specification: Basic Health Monitoring & Error Logging

## Goal

Implement system-wide health monitoring and error logging to provide visibility into service health, track failures across all microservices, generate critical alerts for operational issues, and maintain a complete audit trail of system events. Enable operators to proactively detect and respond to failures (login errors, extraction timeouts, API unavailability, database connectivity issues) before they impact the trading report workflow.

## User Stories

- As a system operator, I want to quickly check the health status of all 5 microservices so I can identify which service is causing issues
- As a system operator, I want to receive email alerts when critical failures occur (login failures, API timeouts, database down) so I can respond quickly to incidents
- As a developer, I want to see detailed error logs categorized by severity so I can debug issues and improve service reliability
- As a system operator, I want to see a consolidated view of recent errors filtered by service and severity so I can audit and investigate failures

## Specific Requirements

**Health Check System Architecture**
- Monitor all 5 services: email-webhook, playwright-scraper, ai-analyzer, notification-service, and n8n
- Minimal granularity: service running status + 3 health signals (service process, database connectivity, external API connectivity)
- Implement `/health` endpoint on each service returning JSON with status and check details
- Central health aggregator endpoint at `/api/v1/health/status` returning status of all services
- Health checks should complete in under 2 seconds; timeout at 5 seconds with service marked as unhealthy
- Store health check results in PostgreSQL for historical trending and audit purposes

**Error Logging Pipeline**
- All errors categorized into 3 severity levels: CRITICAL (system-blocking), ERROR (single-report failures), WARNING (non-blocking issues)
- Log errors to PostgreSQL error_logs table with full context: service name, error type, timestamp, message, stack trace, affected report_id
- Append-only design: errors logged once and never modified (audit trail principle)
- Include correlation IDs for tracing related errors across service boundaries
- Store error metadata as JSONB for extensibility (response codes, retry count, external API errors)
- Error logging should occur within 1 second of failure detection

**Error Classification & Examples**
- CRITICAL: Failed login to trading portal, database connection failure, required API key missing/expired, webhook signature validation failure, service failed to start
- ERROR: Content extraction timeout, analysis API failure, email send failure, Telegram API error, specific report processing failed
- WARNING: Slow response time (> 5s), rate limit triggered, retry attempted, transient API error (will retry), SSL certificate warning

**Alert Generation & Delivery**
- Generate alerts only for CRITICAL severity errors immediately on first occurrence
- Alert format: email to admin with service name, error type, timestamp, error message, affected resource (report_id if applicable)
- Prevent alert spam: batch consecutive failures of same type within 1-hour window; send one summary alert per hour
- Transient failure handling: suppress alerts if error resolves within 5 minutes (auto-recovery)
- Reuse unified notification service for alert email delivery
- Alerts sent within 5 minutes of critical error detection

**Health Check Endpoints & API**
- GET `/health` on each service: minimal response with status and process health
- GET `/api/v1/health/status`: aggregate health of all services with details
- GET `/api/v1/health/errors?severity=CRITICAL&limit=10&hours=24`: retrieve recent errors filtered by severity and time window
- POST `/api/v1/health/check/{service}`: manual trigger for health check of specific service (for N8N integration)
- All health endpoints return consistent JSON format with status, timestamp, and details

**Database Schema for Health & Error Tracking**
- health_checks table: id, service_name, status (up/down/degraded), timestamp, check_duration_ms, details_json
- error_logs table: id, timestamp, service_name, error_type, severity (CRITICAL/ERROR/WARNING), message, context_json, source_report_id, stack_trace, correlation_id
- alert_logs table: id, timestamp, error_id, alert_type, recipient, delivery_status (sent/failed), sent_at, delivery_latency_ms
- All tables use append-only design with created_at timestamps for audit compliance

**Alert Batching & Rate Limiting**
- Track alert state per service + error_type combination: last_alert_sent_at, consecutive_failure_count
- Algorithm: if error same type as previous AND last_alert < 60 minutes AND error still occurring, increment counter but don't send new alert
- On alert resolution: reset consecutive_failure_count and send optional "resolved" notification
- Suppress duplicate alerts for same error within 5-minute window
- Email batching: combine multiple errors into single alert email with formatted table

**Error Retention & Cleanup**
- Maintain 30-day retention window for error logs (30-day rolling window)
- Create cleanup job to archive/delete errors older than 30 days
- Health check history: keep 7 days of health check records for trending
- Provide manual archival endpoint for compliance/regulatory requirements

**Integration with Existing Notification Service**
- Reuse unified notification service for alert email delivery
- Create alert notification request with template type "critical_error_alert"
- Support notification retry logic (use existing retry mechanism)
- Log alert delivery status to alert_logs table
- Track delivery failures separately to prevent lost alerts

**Configuration & Environment Variables**
- HEALTH_CHECK_INTERVAL: seconds between automatic health checks (default: 60)
- HEALTH_CHECK_TIMEOUT: maximum seconds to wait for service response (default: 5)
- ALERT_EMAIL_ADMIN: email address for critical alerts
- ALERT_BATCH_WINDOW: minutes to batch consecutive failures (default: 60)
- ALERT_AUTO_RESOLVE_WINDOW: minutes to suppress re-alerts if error resolved (default: 5)
- ERROR_LOG_RETENTION_DAYS: days to keep error logs (default: 30)
- ENABLE_HEALTH_MONITORING: boolean to enable/disable health checks (default: true)

**Health Check Implementation Details**
- Email-webhook service: check database connectivity, verify webhook endpoint accessible
- Playwright-scraper: check database connectivity, validate playwright browser availability
- AI-analyzer: check database connectivity, verify AI API key configured and responsive
- Notification-service: check database connectivity, test SMTP connectivity, verify Telegram API reachable
- N8N: check service HTTP endpoint, verify PostgreSQL connection from N8N perspective
- Include response time in health check result for performance monitoring

**Error Handling in Each Service**
- Each service wraps critical operations in try-catch blocks
- On exception, log to error_logs table with appropriate severity
- Include correlation ID in logs for tracing across services
- Store error context: user input (sanitized), system state, retry count, external API response
- Include request_id/correlation_id for end-to-end tracing

**N8N Workflow Integration**
- Create N8N workflow node to call `/api/v1/health/status` endpoint
- Display health status in N8N UI for operator monitoring
- Add N8N error handler that logs errors to error_logs table on workflow failure
- Create workflow alarm that sends alert email when critical workflow step fails

**Service Structure & Code Organization**
- Create health-monitoring service: `services/health-monitoring/` with FastAPI app
- Alternatively, add health monitoring to existing api service or credential-service
- Directory structure: src/models.py, src/api/routes.py, src/db/health_repository.py, src/db/error_repository.py, src/db/alert_repository.py
- Background task: periodic health check scheduler running every HEALTH_CHECK_INTERVAL seconds
- Background task: alert generation worker checking for critical errors every 60 seconds
- Background task: error log cleanup running daily at midnight

**Logging Strategy**
- Log all health check attempts with service name, result, duration_ms, and any exceptions
- Log all errors at time of occurrence with full context and stack trace
- Use structured logging with fields: service_name, error_type, severity, correlation_id, report_id
- Log alert generation with error details and recipient
- Log alert delivery attempts with delivery status and latency
- Use get_logger() pattern from existing services for consistency

**Success Metrics & Testing**
- Health endpoints respond in < 2 seconds (95th percentile)
- Errors logged to database within 1 second of occurrence
- Critical errors generate alert email within 5 minutes
- Database query to retrieve recent errors completes in < 500ms
- 30-day retention job runs successfully without data loss
- All 5 services report health correctly in aggregated endpoint
- Alert spam prevention verified: duplicate alerts not sent within 5-minute window
- Batch window verified: 5+ errors of same type within 1 hour produce single alert

## Visual Design

(No visual mockups provided; health monitoring is backend/API service)

## Existing Code to Leverage

**Database Connection & Pool Pattern (services/ai-analyzer/src/db/connection.py)**
- Reuse init_db_pool() and close_db_pool() for health monitoring service database access
- Follow asyncpg connection pooling pattern for performance
- Use pool.execute() for queries in health repository

**Logging Pattern (services/ai-analyzer/src/utils/logger.py)**
- Reuse get_logger() and structured logging pattern
- Create ErrorLogger helper class extending base logger with context fields
- Follow error logging conventions: service_name, error_type, severity, correlation_id

**API Routes Pattern (services/notification-service/src/api/routes.py)**
- Follow APIRouter and endpoint pattern with request/response models
- Return consistent HealthCheckResponse models
- Use HTTPException with appropriate status codes (200, 202, 400, 404, 500, 503)
- Include request_id and correlation_id in all responses

**Notification Service Integration (services/notification-service/src/api/routes.py)**
- Call notification service POST /api/v1/notify endpoint for alert emails
- Reuse NotificationRequest model pattern
- Pass template_type: "critical_error_alert" for alert emails
- Handle notification service failures gracefully (log, don't fail health monitoring)

**Models & Validation (services/notification-service/src/models.py)**
- Follow Pydantic BaseModel pattern for request/response schemas
- Create HealthCheckResponse, ErrorLogEntry, AlertLogEntry models
- Validate severity levels using Enum (CRITICAL, ERROR, WARNING)
- Use Optional[] for nullable fields, List[] for arrays

**Security Events Logging (services/email-webhook/src/db/security_events_repository.py)**
- Reuse append-only table pattern: single INSERT, no UPDATE or DELETE
- Use created_at timestamp and UUID primary key
- Store metadata as JSONB for extensibility
- Create repository pattern for database operations

**Background Task Scheduling (services/email-webhook/src/main.py line 98)**
- Follow asyncio.create_task() pattern for background tasks in lifespan startup
- Implement cleanup loop with while True and asyncio.sleep()
- Catch asyncio.CancelledError on shutdown
- Add logging for task start/stop

**Error Handling (services/ai-analyzer/src/utils/exceptions.py)**
- Extend exception hierarchy: HealthMonitoringError (base), HealthCheckError, AlertGenerationError
- Create specific exception types for different failure modes
- Include error_code and message fields for structured error responses
- Log exception context with extra fields for debugging

**Retry Mechanism (services/notification-service/src/services/retry_scheduler.py)**
- Reuse retry logic for alert delivery through notification service
- Follow exponential backoff pattern: 2^retry_count seconds
- Store retry state in notifications table
- Add max_retries constraint

## Out of Scope

- Advanced metrics collection (CPU, memory, disk usage) - Phase 2+ enhancement
- Real-time dashboard UI (use N8N visualization or future frontend dashboard)
- Telegram alert delivery (Phase 2+, currently email only)
- SMS alerts - Phase 2+ enhancement
- Slack/Discord notifications - Phase 2+ enhancement
- Distributed tracing system (Jaeger, DataDog) - Phase 2+ with dedicated agent
- Performance profiling and optimization - separate analysis phase
- SLA tracking and compliance reporting - Phase 2+ enhancement
- Anomaly detection on error rates - Phase 2+ ML enhancement
- Custom alert rules per service - Phase 2+, currently hardcoded rules only
- Service dependency mapping and cascade failure detection - Phase 2+
- External metrics export (Prometheus scraping) - Phase 2+ enhancement
- End-to-end synthetic monitoring - Phase 2+ with dedicated agent
- Webhook for external alerting systems - Phase 2+ enhancement
