# Task Breakdown: Basic Health Monitoring & Error Logging

## Overview
Total Tasks: 48 | Estimated Duration: 40-60 hours | Recommended Team: 1-2 developers + 1 DevOps engineer

This feature implements system-wide health monitoring, centralized error logging, and alert generation across all 5 microservices. The implementation follows a phased approach: database foundation → health monitoring service → error logging → alert system → API endpoints → background jobs → N8N integration → testing → deployment.

---

## Task List

### Phase 1: Database Setup (Foundational)

**Why**: All subsequent phases depend on database tables for health checks, error logs, and alert tracking. Must be completed first.

**Dependencies**: None

#### Task Group 1.0: Health & Error Log Schema Migration

- [x] 1.0 Complete database migrations for health monitoring
  - [x] 1.1 Write 2-3 focused tests for health check storage
    - Test: storing health check with all required fields
    - Test: retrieving latest health check per service
    - Test: append-only constraint (verify no updates occur)
  - [x] 1.2 Create migration 012_health_monitoring_schema.sql
    - Create `health_checks` table:
      - Columns: id (UUID PK), service_name (VARCHAR), status (VARCHAR: up/down/degraded), check_timestamp (TIMESTAMP), check_duration_ms (INT), details_json (JSONB), created_at (TIMESTAMP)
      - Primary key: id
      - Indexes: (service_name, check_timestamp DESC), (created_at DESC)
      - Constraints: NOT NULL on service_name, status, check_timestamp
    - Create `error_logs` table:
      - Columns: id (UUID PK), error_timestamp (TIMESTAMP), service_name (VARCHAR), error_type (VARCHAR), severity (VARCHAR: CRITICAL/ERROR/WARNING), message (TEXT), context_json (JSONB), source_report_id (UUID, nullable), stack_trace (TEXT, nullable), correlation_id (VARCHAR, nullable), created_at (TIMESTAMP)
      - Primary key: id
      - Indexes: (severity, error_timestamp DESC), (service_name, error_timestamp DESC), (correlation_id), (created_at DESC)
      - Constraints: NOT NULL on error_timestamp, service_name, error_type, severity, message
    - Create `alert_logs` table:
      - Columns: id (UUID PK), error_id (UUID, FK → error_logs.id), alert_timestamp (TIMESTAMP), alert_type (VARCHAR), recipient (VARCHAR), delivery_status (VARCHAR: sent/failed/pending), sent_at (TIMESTAMP, nullable), delivery_latency_ms (INT, nullable), created_at (TIMESTAMP)
      - Primary key: id
      - Indexes: (error_id), (alert_timestamp DESC), (delivery_status), (created_at DESC)
      - Constraints: NOT NULL on error_id, alert_timestamp, alert_type, recipient, delivery_status
      - Foreign key: error_id → error_logs(id) ON DELETE CASCADE
    - Reference: `/agent-os/specs/2025-11-25-postgresql-schema-data-persistence/spec.md`
    - Follow migration pattern from: `/database/migrations/010_create_security_events_table.sql`
  - [x] 1.3 Create migration 013_health_monitoring_state_table.sql
    - Create `alert_state` table for batching/spam prevention:
      - Columns: id (UUID PK), service_name (VARCHAR), error_type (VARCHAR), last_alert_sent_at (TIMESTAMP, nullable), consecutive_failure_count (INT), last_error_timestamp (TIMESTAMP), alert_suppressed_until (TIMESTAMP, nullable), created_at (TIMESTAMP), updated_at (TIMESTAMP)
      - Primary key: id
      - Unique constraint: (service_name, error_type)
      - Indexes: (alert_suppressed_until), (updated_at DESC)
      - Constraints: NOT NULL on service_name, error_type, consecutive_failure_count, created_at
    - Note: This is the ONLY table with UPDATE operations (all others append-only)
  - [x] 1.4 Test migrations run successfully
    - Run ONLY the 2-3 tests written in 1.1
    - Verify all tables created with correct structure: `\dt+ health_checks error_logs alert_logs alert_state`
    - Verify indexes created: `\di+ *_service_name_*, *_error_timestamp_*`
    - Verify foreign key constraint works: test cascading delete

**Acceptance Criteria**:
- The 2-3 tests written in 1.1 pass
- All 4 tables (health_checks, error_logs, alert_logs, alert_state) exist in database
- Indexes created on frequently-queried columns
- Append-only constraints enforced (no updates on health_checks, error_logs tables)
- Foreign key cascade delete works on alert_logs → error_logs

---

### Phase 2: Health Monitoring Service Infrastructure

**Why**: Must establish service structure, database connectivity, and foundational health check logic before implementing specific checks.

**Dependencies**: Phase 1 (database schema)

#### Task Group 2.0: Service Structure & Connection Pooling

- [x] 2.0 Create health-monitoring service directory structure
  - [x] 2.1 Write 2-3 focused tests for database connection pooling
    - Test: connection pool initializes successfully
    - Test: execute query through pool returns valid results
    - Test: connection pool closes gracefully on shutdown
  - [x] 2.2 Create service directory structure
    - Create `/services/health-monitoring/` directory
    - Create subdirectories: src/, src/api/, src/db/, src/services/, src/utils/, tests/
    - Create files:
      - `src/__init__.py`
      - `src/main.py` (FastAPI app entry point)
      - `src/config.py` (configuration with environment variables)
      - `src/models.py` (Pydantic request/response models)
      - `src/db/__init__.py`
      - `src/db/connection.py` (connection pooling, init/close)
      - `src/db/health_repository.py` (store/retrieve health checks)
      - `src/db/error_repository.py` (log errors, retrieve error_logs)
      - `src/db/alert_repository.py` (manage alert_state, log alerts)
      - `src/services/__init__.py`
      - `src/services/health_check_service.py` (orchestrate all health checks)
      - `src/services/error_logger.py` (structured error logging)
      - `src/services/alert_service.py` (alert batching & generation)
      - `src/utils/__init__.py`
      - `src/utils/logger.py` (logging setup)
      - `src/utils/exceptions.py` (custom exception types)
      - `src/api/__init__.py`
      - `src/api/routes.py` (API endpoints)
      - `Dockerfile`
      - `requirements.txt`
      - `tests/__init__.py`
      - `.env.example`
    - Reference pattern: `/services/ai-analyzer/` and `/services/notification-service/`
  - [x] 2.3 Create requirements.txt
    - Dependencies: fastapi, uvicorn, asyncpg, pydantic, python-dotenv, aiohttp (for health checks)
    - Follow version constraints from `/services/ai-analyzer/requirements.txt`
  - [x] 2.4 Create config.py with environment variables
    - `SERVICE_PORT` (default: 8003)
    - `LOG_LEVEL` (default: INFO)
    - `DATABASE_URL` (PostgreSQL connection string)
    - `HEALTH_CHECK_INTERVAL` (default: 60 seconds)
    - `HEALTH_CHECK_TIMEOUT` (default: 5 seconds)
    - `ALERT_EMAIL_ADMIN` (email for critical alerts)
    - `ALERT_BATCH_WINDOW` (default: 60 minutes)
    - `ALERT_AUTO_RESOLVE_WINDOW` (default: 5 minutes)
    - `ERROR_LOG_RETENTION_DAYS` (default: 30)
    - `ENABLE_HEALTH_MONITORING` (default: true)
    - Service URLs for each of 5 services: `EMAIL_WEBHOOK_URL`, `PLAYWRIGHT_SCRAPER_URL`, `AI_ANALYZER_URL`, `NOTIFICATION_SERVICE_URL`, `N8N_URL`
    - Follow pattern from: `/services/ai-analyzer/src/config.py`
  - [x] 2.5 Create src/db/connection.py
    - Implement `init_db_pool()` function
      - Initialize asyncpg connection pool
      - Pool size: 10 connections
      - Follow pattern from: `/services/ai-analyzer/src/db/connection.py`
    - Implement `close_db_pool()` function
      - Gracefully close pool on shutdown
    - Implement `get_pool()` function to retrieve current pool
    - Add error handling and logging
  - [x] 2.6 Test connection pooling
    - Run ONLY the 2-3 tests written in 2.1
    - Verify pool initialization succeeds
    - Verify queries execute through pool
    - Verify pool cleanup on shutdown

**Acceptance Criteria**:
- The 2-3 tests written in 2.1 pass
- Service directory structure created with all required files
- Connection pool initializes and closes without errors
- Configuration loaded from environment variables
- Service can start successfully

---

### Phase 3: Core Health Check Logic

**Why**: Implement health check logic for all 5 services before aggregating into endpoints.

**Dependencies**: Phase 2 (service infrastructure)

#### Task Group 3.0: Health Check Implementation

- [x] 3.0 Implement health checks for all 5 services
  - [x] 3.1 Write 6-8 focused tests for health check logic
    - Test: email-webhook service health check (mock HTTP call)
    - Test: playwright-scraper service health check (mock HTTP call)
    - Test: ai-analyzer service health check (mock HTTP call)
    - Test: notification-service service health check (mock HTTP call)
    - Test: n8n service health check (mock HTTP call)
    - Test: timeout handling (service doesn't respond within 5 seconds)
    - Test: health check result stored to database with duration
  - [x] 3.2 Create src/services/health_check_service.py
    - Implement `HealthCheckService` class:
      - `async def check_email_webhook()` - call GET /health endpoint, verify response
      - `async def check_playwright_scraper()` - call GET /health endpoint, verify response
      - `async def check_ai_analyzer()` - call GET /health endpoint, verify response
      - `async def check_notification_service()` - call GET /health endpoint, verify response
      - `async def check_n8n()` - call GET http://localhost:5678 (check HTTP 200)
    - Each check should:
      - Measure response time in milliseconds
      - Return structured result: {service_name, status, check_duration_ms, details}
      - Timeout after HEALTH_CHECK_TIMEOUT seconds, return status="down"
      - Log result with service name and duration
    - Implement `async def run_all_checks()` → returns list of health check results
    - Use aiohttp for HTTP calls (async)
    - Reference: `/services/notification-service/src/services/notification_service.py`
  - [x] 3.3 Create src/db/health_repository.py
    - Implement `HealthRepository` class:
      - `async def store_health_check(service_name, status, duration_ms, details)` → stores to health_checks table
      - `async def get_latest_health_checks()` → returns latest check per service
      - `async def get_health_history(service_name, hours=24)` → returns all checks in time window
    - Ensure append-only: only INSERT, never UPDATE
    - Use connection pool from `/src/db/connection.py`
    - Include proper error handling and logging
  - [x] 3.4 Create src/models.py with request/response schemas
    - Define `HealthCheckResponse` model:
      ```python
      class HealthCheckResponse(BaseModel):
          service_name: str
          status: Literal["up", "down", "degraded"]
          check_timestamp: datetime
          check_duration_ms: int
          details: Optional[dict] = None
      ```
    - Define `AggregateHealthResponse` model:
      ```python
      class AggregateHealthResponse(BaseModel):
          timestamp: datetime
          overall_status: Literal["healthy", "degraded", "unhealthy"]
          services: List[HealthCheckResponse]
      ```
    - Define `ErrorLogEntry` model (used in Phase 3)
    - Define `AlertLogEntry` model (used in Phase 4)
    - Follow pattern from: `/services/notification-service/src/models.py`
  - [x] 3.5 Test health check logic
    - Run ONLY the 6-8 tests written in 3.1
    - Verify each service health check works with mocked HTTP calls
    - Verify timeout handling (service marked as "down" after 5 seconds)
    - Verify health check results stored to database
    - Verify response times captured correctly

**Acceptance Criteria**:
- The 6-8 tests written in 3.1 pass
- Health checks implemented for all 5 services
- Each check completes within 5 seconds, returns status (up/down/degraded)
- Health check results stored to database
- Response times captured in milliseconds
- Timeout handling works (marked as down after 5 seconds)

---

### Phase 4: Error Logging & Classification

**Why**: Establish error logging foundation before implementing alert generation.

**Dependencies**: Phase 2 (service infrastructure)

#### Task Group 4.0: Error Logging Pipeline

- [x] 4.0 Implement error logging system
  - [x] 4.1 Write 4-6 focused tests for error logging
    - Test: error logged with all required fields (service_name, error_type, severity, message)
    - Test: error with correlation_id tracked for tracing
    - Test: error context stored as JSONB metadata
    - Test: retrieve errors filtered by severity
    - Test: retrieve errors filtered by service and time window
  - [x] 4.2 Create src/services/error_logger.py
    - Implement `ErrorLogger` class:
      - `async def log_error(service_name, error_type, severity, message, context=None, report_id=None, correlation_id=None, stack_trace=None)` → inserts into error_logs table
      - Return: error_id (UUID) for alert correlation
    - Validate severity: must be CRITICAL, ERROR, or WARNING
    - Include timestamp in UTC
    - Log to both database and application logger
    - Ensure idempotent (safe to call multiple times with same error)
  - [x] 4.3 Create src/db/error_repository.py
    - Implement `ErrorRepository` class:
      - `async def log_error(error_data)` → insert into error_logs table
      - `async def get_recent_errors(severity=None, service=None, hours=24, limit=100)` → retrieve with filtering
      - `async def get_error_by_id(error_id)` → retrieve single error by ID
      - `async def get_errors_by_correlation_id(correlation_id)` → retrieve related errors
    - Ensure append-only: only INSERT, never UPDATE/DELETE
    - Create proper indexes for query performance
  - [x] 4.4 Create src/utils/exceptions.py
    - Define custom exception types:
      - `HealthMonitoringError` (base)
      - `HealthCheckError` (extends HealthMonitoringError)
      - `ErrorLoggingError` (extends HealthMonitoringError)
      - `AlertGenerationError` (extends HealthMonitoringError)
    - Each exception includes: error_code, message, details (dict)
    - Follow pattern from: `/services/ai-analyzer/src/utils/exceptions.py`
  - [x] 4.5 Add error logging to each microservice
    - For each service: email-webhook, playwright-scraper, ai-analyzer, notification-service
    - Add import: `from health_monitoring.error_logger import ErrorLogger`
    - Wrap critical operations in try-catch:
      - Email parsing/validation
      - Portal login/authentication
      - Content extraction
      - AI API calls
      - Email/Telegram sending
    - On exception, call: `await error_logger.log_error(service_name="...", error_type="...", severity="...", message=str(e), context={...}, stack_trace=traceback.format_exc())`
    - Include correlation_id from request context (if available)
    - Include report_id if error relates to specific report
  - [x] 4.6 Test error logging
    - Run ONLY the 4-6 tests written in 4.1
    - Verify errors logged with all required fields
    - Verify correlation tracking works
    - Verify JSONB context stored and retrievable
    - Verify filtering by severity/service/time works
    - Verify append-only constraint (no updates)

**Acceptance Criteria**:
- The 4-6 tests written in 4.1 pass
- Error logging works across all 5 services
- Errors stored to database within 1 second of occurrence
- All required fields captured: service_name, error_type, severity, message, timestamp
- Correlation IDs enable tracing across services
- Context metadata stored as JSONB
- Errors are append-only (never modified)

---

### Phase 5: Alert Generation & Delivery

**Why**: Implement alert system with batching and spam prevention.

**Dependencies**: Phase 4 (error logging), Phase 1 (alert_state table)

#### Task Group 5.0: Alert Batching & Generation

- [x] 5.0 Implement alert generation with spam prevention
  - [x] 5.1 Write 5-7 focused tests for alert batching
    - Test: first CRITICAL error generates alert immediately
    - Test: duplicate errors within 5 minutes don't generate new alert
    - Test: same error type within 1-hour window batched into single alert
    - Test: error resolved (no new errors for 5 minutes) resets counter
    - Test: alert state correctly tracks consecutive_failure_count
    - Test: alert_suppressed_until prevents alerts during suppression window
  - [x] 5.2 Create src/db/alert_repository.py
    - Implement `AlertRepository` class:
      - `async def get_alert_state(service_name, error_type)` → retrieve current state
      - `async def upsert_alert_state(service_name, error_type, data)` → create or update alert state
      - `async def log_alert(error_id, alert_type, recipient, delivery_status)` → insert into alert_logs table
      - `async def update_alert_delivery_status(alert_id, delivery_status, sent_at, latency_ms)` → update delivery status (only table with updates besides alert_state)
      - `async def get_recent_alerts(limit=100, hours=24)` → retrieve recent alerts
  - [x] 5.3 Create src/services/alert_service.py
    - Implement `AlertService` class with batching algorithm:
      - `async def check_and_generate_alerts()` → run periodically to check for CRITICAL errors
      - For each CRITICAL error since last check:
        - Get alert_state for (service_name, error_type)
        - If last_alert < 5 minutes ago AND error still same type → skip (already sent recently)
        - If last_alert < 60 minutes ago AND error type same → increment counter, don't send (batch)
        - If last_alert >= 60 minutes ago OR no previous alert → generate new alert, update state
      - On alert resolution (no errors for 5 minutes) → reset consecutive_failure_count
      - Implementation:
        - Query error_logs for CRITICAL errors in last hour
        - For each unique (service_name, error_type) combination:
          - Check alert_state table
          - Apply batching rules above
          - Generate alert if needed
          - Update alert_state with new values
      - Return: list of alerts to send
  - [x] 5.4 Integrate with notification service
    - Implement `async def send_alerts(alerts)` function in alert_service.py
    - For each alert to send:
      - Call notification service: `POST /api/v1/notify` endpoint
      - Request body:
        ```json
        {
          "template_type": "critical_error_alert",
          "recipient": "admin@example.com",
          "context": {
            "service_name": "...",
            "error_type": "...",
            "error_message": "...",
            "timestamp": "...",
            "consecutive_failures": 5
          }
        }
        ```
      - Log response to alert_logs table
      - Capture latency_ms and delivery_status
      - Handle notification service failures gracefully (log, don't fail)
    - Reference: `/services/notification-service/src/services/notification_service.py`
  - [x] 5.5 Test alert generation
    - Run ONLY the 5-7 tests written in 5.1
    - Verify first CRITICAL error generates alert
    - Verify batching prevents duplicate alerts within 5 minutes
    - Verify batching combines multiple errors within 1-hour window
    - Verify alert state tracks consecutive_failure_count
    - Verify alert_suppressed_until blocks alerts during suppression

**Acceptance Criteria**:
- The 5-7 tests written in 5.1 pass
- Alert batching algorithm works correctly
- Spam prevention enforced (no duplicates within 5 minutes)
- Alerts generated only for CRITICAL severity errors
- Alert delivery logged to alert_logs table
- Delivery status tracked (sent/failed/pending)
- Alerts sent within 5 minutes of error detection

---

### Phase 6: API Endpoints

**Why**: Expose health and error data through REST API for operators and N8N integration.

**Dependencies**: Phase 3 (health checks), Phase 4 (error logging), Phase 5 (alerts)

#### Task Group 6.0: Health & Error API

- [x] 6.0 Implement API endpoints
  - [x] 6.1 Write 4-6 focused tests for API endpoints
    - Test: GET /health returns service health (minimal response)
    - Test: GET /api/v1/health/status returns aggregate health of all services
    - Test: GET /api/v1/health/errors with filtering by severity and time window
    - Test: POST /api/v1/health/check/{service} triggers manual health check
    - Test: error handling returns 400/404/500 with proper format
  - [x] 6.2 Create src/main.py (FastAPI app entry point)
    - Follow pattern from: `/services/ai-analyzer/src/main.py`
    - Setup lifespan context manager with:
      - Startup: initialize DB pool, start background tasks
      - Shutdown: close DB pool, cancel background tasks
    - Add CORS middleware
    - Include routes from `/src/api/routes.py`
    - Add logging for startup/shutdown events
  - [x] 6.3 Create src/api/routes.py with health endpoints
    - Implement GET `/health` endpoint:
      - Return minimal response: {status: "ok", timestamp, service_name: "health-monitoring"}
      - Fast check (< 100ms) - just verify service running
      - Use for docker healthcheck
    - Implement GET `/api/v1/health/status` endpoint:
      - Return AggregateHealthResponse
      - Include health status of all 5 services
      - Calculate overall_status: "healthy" (all up), "degraded" (some up), "unhealthy" (all down)
      - Include timestamp of aggregated check
      - Response status: 200 if all services up, 503 if any down
    - Implement GET `/api/v1/health/errors` endpoint:
      - Query parameters: severity (optional), service (optional), hours (default: 24), limit (default: 10)
      - Return: {timestamp, count, errors: [ErrorLogEntry]}
      - Filter by severity if provided (CRITICAL, ERROR, WARNING)
      - Filter by service if provided
      - Limit time window to last N hours
      - Sort by timestamp DESC
      - Response status: 200 (success), 400 (invalid params)
    - Implement POST `/api/v1/health/check/{service}` endpoint:
      - Parameter: service (required) - one of: email-webhook, playwright-scraper, ai-analyzer, notification-service, n8n
      - Trigger manual health check for specified service
      - Return: HealthCheckResponse
      - Store result to health_checks table
      - Response status: 200 (success), 400 (invalid service), 408 (timeout)
    - Add request/response models validation
    - Add proper HTTP status codes
    - Include request_id/correlation_id in responses
    - Reference: `/services/notification-service/src/api/routes.py`
  - [x] 6.4 Test API endpoints
    - Run ONLY the 4-6 tests written in 6.1
    - Verify GET /health returns 200 quickly
    - Verify GET /api/v1/health/status aggregates all services
    - Verify GET /api/v1/health/errors filters by severity/service/time
    - Verify POST /api/v1/health/check/{service} triggers check
    - Verify error responses have correct status codes

**Acceptance Criteria**:
- The 4-6 tests written in 6.1 pass
- GET /health returns 200 in < 100ms
- GET /api/v1/health/status returns aggregate health of all 5 services
- GET /api/v1/health/errors supports filtering and pagination
- POST /api/v1/health/check/{service} triggers manual check
- All endpoints return consistent JSON format
- Proper error handling with appropriate status codes

---

### Phase 7: Background Tasks & Cleanup

**Why**: Implement recurring jobs for continuous health monitoring, alert generation, and data retention.

**Dependencies**: Phase 3 (health checks), Phase 5 (alerts), Phase 1 (database)

#### Task Group 7.0: Background Job Scheduling

- [x] 7.0 Implement background tasks and cleanup
  - [x] 7.1 Write 3-4 focused tests for background jobs
    - Test: health check scheduler runs at correct interval
    - Test: alert generator checks for CRITICAL errors periodically
    - Test: error log cleanup runs daily and removes old records
  - [x] 7.2 Implement health check scheduler in src/main.py
    - Background task in lifespan startup:
      ```python
      async def health_check_loop():
          while True:
              try:
                  results = await health_check_service.run_all_checks()
                  for result in results:
                      await health_repository.store_health_check(...)
                  await asyncio.sleep(HEALTH_CHECK_INTERVAL)
              except asyncio.CancelledError:
                  logger.info("Health check loop cancelled")
                  break
              except Exception as e:
                  logger.error(f"Health check loop error: {e}")
                  await asyncio.sleep(HEALTH_CHECK_INTERVAL)
      ```
    - Run every HEALTH_CHECK_INTERVAL seconds (default: 60)
    - Catch and log errors without failing
    - Reference pattern from: `/services/email-webhook/src/main.py` line 98
  - [x] 7.3 Implement alert generation scheduler in src/main.py
    - Background task in lifespan startup:
      - Run alert service: `await alert_service.check_and_generate_alerts()`
      - Collect alerts to send
      - Send via notification service: `await alert_service.send_alerts(alerts)`
    - Run every 60 seconds
    - Catch and log errors without failing
  - [x] 7.4 Implement error log cleanup job in src/services/cleanup_service.py
    - Implement `CleanupService` class:
      - `async def cleanup_error_logs()` - delete error_logs older than ERROR_LOG_RETENTION_DAYS
      - `async def cleanup_health_checks()` - delete health_checks older than 7 days
      - Return: count of records deleted
    - Include logging with record counts
    - Implementation:
      ```sql
      DELETE FROM error_logs
      WHERE created_at < NOW() - INTERVAL '30 days'
      ```
    - Run daily at midnight (00:00 UTC)
    - Background task in lifespan startup
  - [x] 7.5 Implement manual archival endpoint
    - POST `/api/v1/health/archive/{table_name}` endpoint:
      - Parameter: table_name (error_logs or health_checks)
      - Optional query param: before_date (ISO format, default: 30 days ago)
      - Archive/delete records before specified date
      - Return: {archived_count, affected_tables}
      - Response status: 200 (success), 400 (invalid table/date)
    - Useful for compliance and regulatory requirements
  - [x] 7.6 Test background jobs
    - Run ONLY the 3-4 tests written in 7.1
    - Verify health check scheduler runs at correct interval
    - Verify alert generator executes without errors
    - Verify cleanup job deletes old records correctly

**Acceptance Criteria**:
- The 3-4 tests written in 7.1 pass
- Health check scheduler runs every HEALTH_CHECK_INTERVAL seconds
- Alert generation scheduler runs every 60 seconds
- Error log cleanup runs daily, removes records older than 30 days
- Health check cleanup removes records older than 7 days
- Background jobs log execution with counts
- Manual archival endpoint works for compliance

---

### Phase 8: Docker & Service Configuration

**Why**: Enable service to run in Docker Compose alongside other microservices.

**Dependencies**: Phase 6 (API endpoints), Phase 7 (background jobs)

#### Task Group 8.0: Containerization & Deployment

- [x] 8.0 Create Docker configuration
  - [x] 8.1 Write 1-2 focused tests for Docker build/startup
    - Test: Docker image builds successfully
    - Test: service starts and becomes healthy
  - [x] 8.2 Create Dockerfile for health-monitoring service
    - Base image: python:3.11-slim
    - Working directory: /app
    - Copy requirements.txt, install dependencies
    - Copy source code
    - Expose port 8003
    - CMD: `uvicorn src.main:app --host 0.0.0.0 --port 8003`
    - Follow pattern from: `/services/ai-analyzer/Dockerfile`
  - [x] 8.3 Add health-monitoring service to docker-compose.yml
    - Service name: health-monitoring
    - Build: ./services/health-monitoring
    - Container name: trading-health-monitoring
    - Ports: 8003:8003
    - Environment variables:
      - SERVICE_PORT=8003
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - DATABASE_URL (from postgres config)
      - HEALTH_CHECK_INTERVAL=60
      - HEALTH_CHECK_TIMEOUT=5
      - ALERT_EMAIL_ADMIN=${ALERT_EMAIL_ADMIN:-admin@example.com}
      - ALERT_BATCH_WINDOW=60
      - ALERT_AUTO_RESOLVE_WINDOW=5
      - ERROR_LOG_RETENTION_DAYS=30
      - ENABLE_HEALTH_MONITORING=true
      - EMAIL_WEBHOOK_URL=http://email-webhook:8001
      - PLAYWRIGHT_SCRAPER_URL=http://playwright-scraper:8002
      - AI_ANALYZER_URL=http://ai-analyzer:8000
      - NOTIFICATION_SERVICE_URL=http://notification-service:8001
      - N8N_URL=http://n8n:5678
    - Networks: trading-network
    - Depends_on: postgres (service_healthy)
    - Healthcheck:
      - Test: `["CMD", "curl", "-f", "http://localhost:8003/health"]`
      - Interval: 30s
      - Timeout: 10s
      - Retries: 3
    - Memory limit: 512M
    - Volumes for hot-reload in dev:
      - `./services/health-monitoring/src:/app/src:cached`
    - Reference pattern from: `/docker-compose.yml` (email-webhook service)
  - [x] 8.4 Test Docker configuration
    - Run ONLY the 1-2 tests written in 8.1
    - Build Docker image: `docker build -t trading-health-monitoring ./services/health-monitoring`
    - Start service: `docker-compose up health-monitoring`
    - Verify service becomes healthy (healthcheck passes)
    - Verify port 8003 accessible: `curl http://localhost:8003/health`

**Acceptance Criteria**:
- The 1-2 tests written in 8.1 pass
- Docker image builds successfully
- Service container runs and becomes healthy
- Healthcheck passes within 60 seconds
- API endpoints accessible on port 8003
- Service can communicate with other services via docker network

---

### Phase 9: N8N Workflow Integration

**Why**: Enable operators to view health status and error alerts in N8N workflow UI.

**Dependencies**: Phase 6 (API endpoints)

#### Task Group 9.0: N8N Workflow Nodes

- [x] 9.0 Create N8N workflow integration
  - [x] 9.1 Write 1-2 focused tests for N8N API calls
    - Test: N8N can call /api/v1/health/status and receive response
    - Test: N8N can call /api/v1/health/errors and filter by severity
  - [x] 9.2 Create N8N workflow node for health status
    - Node type: HTTP Request (built-in N8N node)
    - Configuration:
      - Method: GET
      - URL: `{{ $env.HEALTH_MONITORING_URL }}/api/v1/health/status`
      - Headers: Content-Type: application/json
      - Authentication: none
    - Output: aggregate health status with all 5 services
    - Use in dashboard/monitoring workflows
    - Optional: add conditional logic to alert if any service degraded
  - [x] 9.3 Create N8N workflow for error alerts
    - Workflow purpose: detect and alert on new CRITICAL errors
    - Steps:
      1. Scheduler: run every 5 minutes
      2. HTTP Request: GET /api/v1/health/errors?severity=CRITICAL&hours=1
      3. Filter: check for new errors since last check (compare timestamps)
      4. Email alert: format and send alert if new errors found
      5. Database: log alert sent to N8N execution log
    - Error handling: log any workflow failures
    - Node references:
      - Scheduler node: interval-based trigger
      - HTTP Request node: call health-monitoring API
      - Filter node: check for new errors
      - Email node: send alert (use notification-service or SMTP)
  - [x] 9.4 Create N8N error handler workflow
    - Trigger: on workflow error
    - Steps:
      1. Capture workflow name, error message, timestamp
      2. Call health-monitoring: POST /api/v1/health/check/{service}
      3. Log error to health-monitoring database
      4. Send notification if service health degraded
    - Purpose: ensure N8N failures are logged to health monitoring system
  - [x] 9.5 Create N8N critical alarm workflow
    - Purpose: escalate CRITICAL errors with special handling
    - Trigger: health status endpoint shows service down
    - Steps:
      1. Get health status: call /api/v1/health/status
      2. Check if any service status == "down"
      3. If so: send urgent email alert with service details
      4. Log alarm event to database
      5. Optional: trigger additional incident response (e.g., restart service)
  - [x] 9.6 Test N8N integration
    - Run ONLY the 1-2 tests written in 9.1
    - Verify N8N can reach health-monitoring endpoints
    - Verify workflow nodes execute successfully
    - Verify response data parsed correctly
    - Execute test workflows in N8N UI and verify results

**Acceptance Criteria**:
- The 1-2 tests written in 9.1 pass
- N8N workflow nodes can call all health-monitoring API endpoints
- Error alert workflow detects and notifies on CRITICAL errors
- Health status displayed in N8N dashboards
- N8N workflow failures logged to health monitoring system

---

### Phase 10: Testing & Validation

**Why**: Ensure all components work together and meet performance requirements.

**Dependencies**: All previous phases

#### Task Group 10.0: Integration & Performance Testing

- [x] 10.0 Write integration tests and validate feature
  - [x] 10.1 Write focused integration tests (max 10 tests total)
    - Test: end-to-end health check cycle (check → store → retrieve)
    - Test: error logging in one service visible in aggregated errors API
    - Test: CRITICAL error generates alert within 5 minutes
    - Test: alert spam prevention (5+ errors of same type within 1 hour → single alert)
    - Test: manual health check trigger via API works
    - Test: error filters work correctly (severity, service, time window)
    - Test: background health check scheduler runs continuously
    - Test: cleanup job removes old error logs correctly
    - Test: N8N can retrieve health status
    - Test: correlation IDs enable cross-service error tracing
  - [x] 10.2 Performance validation
    - Run health check aggregator → should complete in < 2 seconds
    - Run error retrieval query → should complete in < 500ms
    - Verify database indexes working (check EXPLAIN plans)
    - Measure alert latency → should be < 5 minutes from error detection
    - Load test: simulate multiple errors per second → verify no data loss
  - [x] 10.3 Database verification
    - Verify all 4 tables exist with correct schema
    - Verify indexes on health_checks (service_name, created_at)
    - Verify indexes on error_logs (severity, service_name, created_at)
    - Verify foreign key constraint error_logs → alert_logs
    - Test append-only constraint: attempt UPDATE on health_checks → should fail
    - Test cascade delete: delete error → verify alert_logs record deleted
  - [x] 10.4 Run feature-specific tests only
    - Run ONLY tests written in phases 1-9
    - Expected total: approximately 30-45 tests maximum
    - All tests should pass
    - Do NOT run entire application test suite

**Acceptance Criteria**:
- All feature-specific tests pass (30-45 tests total)
- Health endpoints respond in < 2 seconds (95th percentile)
- Error retrieval completes in < 500ms
- Alerts generated within 5 minutes of CRITICAL error
- Alert batching prevents duplicate alerts within 5 minutes
- Database queries use indexes (verified via EXPLAIN)
- No data loss under load
- Append-only constraints enforced

---

### Phase 11: Documentation & Deployment

**Why**: Document the feature and prepare for production deployment.

**Dependencies**: All previous phases

#### Task Group 11.0: Documentation & Environment Setup

- [x] 11.0 Complete documentation and environment setup
  - [x] 11.1 Update .env.example with new variables
    - Add all HEALTH_MONITORING_* variables
    - Example values for EMAIL_WEBHOOK_URL, PLAYWRIGHT_SCRAPER_URL, etc.
    - ALERT_EMAIL_ADMIN with example email
    - HEALTH_CHECK_INTERVAL, HEALTH_CHECK_TIMEOUT
    - ERROR_LOG_RETENTION_DAYS
    - Comment each variable with brief description
    - Reference: `//.env.example`
  - [x] 11.2 Update docker-compose.yml service definitions
    - Add health-monitoring service config (completed in Phase 8)
    - Ensure all 5 monitored services have `/health` endpoint
    - Add to email-webhook, playwright-scraper, ai-analyzer, notification-service if missing
    - Verify n8n has accessible health endpoint
    - Test: `docker-compose config` validates without errors
  - [x] 11.3 Update existing services with health check endpoints
    - Add GET `/health` endpoint to each of 5 services if not already present
    - Response format: `{status: "ok", timestamp, service_name}`
    - Should be fast (< 100ms) - just return OK
    - Add to: email-webhook, playwright-scraper, ai-analyzer, notification-service
    - For n8n: just check if HTTP 200 from main endpoint
  - [x] 11.4 Create HEALTH_MONITORING.md user manual
    - Document health monitoring feature for operators
    - Include sections:
      - Overview: what health monitoring does
      - Architecture: how health checks, error logging, and alerts work
      - Configuration: environment variables and setup
      - API Reference: all endpoints with examples
      - Health Check Details: what each service checks
      - Alert Handling: how alerts are generated and batched
      - Troubleshooting: common issues and solutions
      - Monitoring: how to use N8N dashboards
    - Include curl examples for API endpoints:
      ```bash
      # Check health of all services
      curl http://localhost:8003/api/v1/health/status

      # Get recent CRITICAL errors
      curl 'http://localhost:8003/api/v1/health/errors?severity=CRITICAL&hours=24'

      # Trigger health check for specific service
      curl -X POST http://localhost:8003/api/v1/health/check/ai-analyzer
      ```
  - [x] 11.5 Update CLAUDE.md with health monitoring setup
    - Add Health Monitoring section with:
      - Quick start: `make dev` includes health-monitoring service
      - Make targets:
        - `make logs-service SERVICE=health-monitoring`
        - `make shell SERVICE=health-monitoring` (if needed)
      - Testing health monitoring: how to run feature tests
      - API reference: all endpoints
      - Troubleshooting: common setup issues
  - [x] 11.6 Create migration script for existing deployments
    - Script: `/database/scripts/migrate_to_health_monitoring.sh`
    - Purpose: run database migrations on existing deployments
    - Steps:
      1. Backup existing database
      2. Run migrations 012 and 013
      3. Verify tables created
      4. Test API endpoints
    - Include safety checks and rollback instructions

**Acceptance Criteria**:
- .env.example has all health monitoring variables with descriptions
- docker-compose.yml includes health-monitoring service
- All 5 monitored services have GET /health endpoint
- HEALTH_MONITORING.md documents feature for operators
- CLAUDE.md updated with setup and testing instructions
- Migration script tested and verified

---

## Execution Summary

### Recommended Implementation Order

**Week 1: Foundation (Phase 1-2)**
- Phase 1: Database schema → 4-6 hours
- Phase 2: Service infrastructure → 6-8 hours

**Week 2: Core Features (Phase 3-5)**
- Phase 3: Health check logic → 8-10 hours
- Phase 4: Error logging → 6-8 hours
- Phase 5: Alert generation → 8-10 hours

**Week 3: API & Operations (Phase 6-7)**
- Phase 6: API endpoints → 6-8 hours
- Phase 7: Background jobs → 4-6 hours

**Week 4: Deployment & Integration (Phase 8-11)**
- Phase 8: Docker configuration → 3-4 hours
- Phase 9: N8N integration → 4-6 hours
- Phase 10: Testing & validation → 6-8 hours
- Phase 11: Documentation → 4-6 hours

**Total Estimated Effort**: 40-60 hours for 1-2 developers

### Parallelizable Tasks

These tasks can run in parallel:
- Phase 3 (health checks for different services) - can assign one per developer
- Phase 4 (error logging in different services) - can parallelize service integration
- Phase 9 (N8N workflows) - can be done concurrently with Phase 8

### Key Dependencies

```
Phase 1 (Database)
  ├─ Phase 2 (Infrastructure)
  │  ├─ Phase 3 (Health Checks)
  │  └─ Phase 4 (Error Logging)
  │     ├─ Phase 5 (Alerts)
  │     │  └─ Phase 6 (API)
  │     │     └─ Phase 7 (Background Jobs)
  │     │        ├─ Phase 8 (Docker)
  │     │        ├─ Phase 9 (N8N)
  │     │        ├─ Phase 10 (Testing)
  │     │        └─ Phase 11 (Documentation)
```

---

## File Paths Reference

Key files created in this feature:

### New Service Files
- `/services/health-monitoring/src/main.py` - FastAPI app entry point
- `/services/health-monitoring/src/config.py` - Configuration management
- `/services/health-monitoring/src/models.py` - Request/response schemas
- `/services/health-monitoring/src/db/connection.py` - Database connection pool
- `/services/health-monitoring/src/db/health_repository.py` - Health check data access
- `/services/health-monitoring/src/db/error_repository.py` - Error logging data access
- `/services/health-monitoring/src/db/alert_repository.py` - Alert state management
- `/services/health-monitoring/src/services/health_check_service.py` - Health check logic
- `/services/health-monitoring/src/services/error_logger.py` - Error logging service
- `/services/health-monitoring/src/services/alert_service.py` - Alert generation
- `/services/health-monitoring/src/services/cleanup_service.py` - Data cleanup jobs
- `/services/health-monitoring/src/utils/logger.py` - Logging setup
- `/services/health-monitoring/src/utils/exceptions.py` - Custom exceptions
- `/services/health-monitoring/src/api/routes.py` - API endpoints
- `/services/health-monitoring/Dockerfile` - Container configuration
- `/services/health-monitoring/requirements.txt` - Python dependencies
- `/services/health-monitoring/tests/` - Test suite

### Database Files
- `/database/migrations/012_health_monitoring_schema.sql` - Health/error tables
- `/database/migrations/013_health_monitoring_state_table.sql` - Alert state table
- `/database/scripts/migrate_to_health_monitoring.sh` - Migration script for deployments

### Configuration Files
- `/docker-compose.yml` - Updated with health-monitoring service
- `/.env.example` - Updated with health monitoring variables

### Documentation Files
- `/HEALTH_MONITORING.md` - Operator manual
- `/CLAUDE.md` - Updated developer guide
- `/agent-os/specs/2025-12-03-basic-health-monitoring-error-logging/tasks.md` - This file

---

## Success Metrics

### Functional Metrics
- All 5 services report health status correctly in aggregated endpoint
- Health endpoints respond in < 2 seconds (95th percentile)
- CRITICAL errors generate alert email within 5 minutes
- Alert batching prevents duplicate alerts within 5-minute window
- Error logs retained for 30 days, health checks for 7 days
- No alert spam: maximum 1 alert per service per hour for same error type

### Quality Metrics
- 30-45 feature-specific tests pass
- All database migrations run without errors
- Append-only constraint prevents accidental data modification
- Error correlation IDs enable tracing across services
- Background jobs run without disruption

### Operational Metrics
- Health monitoring service uptime: 99.5%+
- Database queries use indexes (verified via EXPLAIN)
- Alert delivery latency: < 5 minutes from error detection
- Manual archival: 0 data loss during retention cleanup

---

## Notes for Implementation

### Important Considerations

1. **Append-Only Design**: error_logs and health_checks tables should ONLY support INSERT operations. The only exception is alert_logs (for delivery status) and alert_state (for batching state). This maintains audit trail integrity.

2. **Correlation IDs**: Ensure every error carries a correlation_id that matches the HTTP request that triggered it. This enables tracing related errors across service boundaries.

3. **Timeout Handling**: All health checks must timeout after HEALTH_CHECK_TIMEOUT seconds (default: 5s). A service that doesn't respond within 5 seconds should be marked as "down".

4. **Alert Batching Algorithm**: The 1-hour batching window is critical to prevent alert spam. Multiple errors of the same type from the same service within an hour should generate only ONE alert.

5. **Graceful Degradation**: If notification service fails, alert_service should log the error but not crash. The health monitoring system must continue operating.

6. **Database Index Strategy**: Create indexes on:
   - error_logs: (severity, created_at DESC), (service_name, created_at DESC), (correlation_id)
   - health_checks: (service_name, created_at DESC), (created_at DESC)
   - alert_logs: (error_id), (created_at DESC), (delivery_status)

7. **Background Task Cancellation**: When service shuts down, use asyncio.CancelledError to gracefully stop background tasks. Don't force-kill them.

8. **Error Context**: Include relevant context in error_json field:
   - For login errors: portal_name, retry_count (don't include password!)
   - For API errors: response_code, response_body (first 500 chars)
   - For timeouts: elapsed_seconds, expected_timeout
   - For extraction errors: url, html_length, error_location

### Code Reuse Patterns

- **Database Connection Pool**: Reuse pattern from `/services/ai-analyzer/src/db/connection.py`
- **Logging Setup**: Reuse pattern from `/services/ai-analyzer/src/utils/logger.py`
- **FastAPI App**: Reuse pattern from `/services/ai-analyzer/src/main.py`
- **API Routes**: Reuse pattern from `/services/notification-service/src/api/routes.py`
- **Models/Validation**: Reuse pattern from `/services/notification-service/src/models.py`
- **Repository Pattern**: Reuse pattern from `/services/email-webhook/src/db/security_events_repository.py`
- **Background Task Scheduling**: Reuse pattern from `/services/email-webhook/src/main.py` line 98
- **Exception Handling**: Reuse pattern from `/services/ai-analyzer/src/utils/exceptions.py`
- **Notification Service Integration**: Call pattern from `/services/notification-service/src/api/routes.py`

### Testing Strategy

- Write 2-8 focused tests per task group (NOT comprehensive coverage)
- Focus on critical paths: health check → storage → retrieval
- Mock external service calls (don't test network)
- Use pytest with async support
- Limit tests to feature-specific scenarios
- Skip edge cases, performance tests until separate testing phase

---

## Version Control Notes

When creating commits for this feature, use clear messages:
- "Phase 1: Create database schema for health monitoring and error logging"
- "Phase 2: Implement health-monitoring service infrastructure"
- "Phase 3: Implement health checks for all 5 services"
- "Phase 4: Add error logging pipeline to microservices"
- "Phase 5: Implement alert generation with spam prevention"
- "Phase 6: Add API endpoints for health and error data"
- "Phase 7: Implement background jobs and data cleanup"
- "Phase 8: Add health-monitoring to Docker Compose"
- "Phase 9: Integrate health monitoring with N8N workflows"
- "Phase 10: Add integration tests and validation"
- "Phase 11: Complete documentation and deployment setup"
