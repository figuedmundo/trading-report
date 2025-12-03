# Health Monitoring & Error Logging - Deployment Checklist

This document provides step-by-step instructions for deploying the health monitoring feature to a new environment.

## Pre-Deployment Prerequisites

### System Requirements
- [ ] Docker and Docker Compose installed
- [ ] PostgreSQL 13+ (via Docker or external)
- [ ] Python 3.11+
- [ ] At least 2GB free disk space
- [ ] All required environment variables configured
- [ ] Email/SMTP provider configured (for alert delivery)

### Dependencies Installed
- [ ] PostgreSQL running and accessible
- [ ] All microservices built (email-webhook, playwright-scraper, ai-analyzer, notification-service, n8n)
- [ ] Python dependencies installed: `pip install -r services/health-monitoring/requirements.txt`

### Network & Ports
- [ ] Port 8003 available for health-monitoring service
- [ ] Port 5432 available for PostgreSQL
- [ ] Port 5678 available for N8N
- [ ] All service ports (8000, 8001, 8002) available
- [ ] Firewall rules allow inter-service communication
- [ ] Email service (SMTP) accessible from Docker network

### Credentials & Configuration
- [ ] POSTGRES_PASSWORD configured
- [ ] TRADING_USER_PASSWORD configured
- [ ] ALERT_EMAIL_ADMIN configured
- [ ] SMTP_HOST, SMTP_USER, SMTP_PASSWORD configured
- [ ] .env file created from .env.example
- [ ] All required environment variables set

---

## Step 1: Pre-Flight Checks

### 1.1 Verify Existing Services
```bash
# Check all services are running
docker-compose ps

# Should show:
# - postgres (healthy)
# - n8n (healthy)
# - email-webhook (healthy)
# - playwright-scraper (healthy)
# - ai-analyzer (healthy)
# - notification-service (healthy)
# - health-monitoring (should start in this deployment)
```

**Checklist**:
- [ ] All existing services running
- [ ] Database is healthy
- [ ] No port conflicts

### 1.2 Verify Database Access
```bash
# Test database connectivity
make db-shell

# In psql prompt:
SELECT version();
\dt  # List all tables
\q   # Exit
```

**Checklist**:
- [ ] Can connect to database
- [ ] Database version is 13+
- [ ] Existing tables visible

### 1.3 Verify Network Connectivity
```bash
# Test inter-service connectivity
docker-compose exec email-webhook curl -f http://notification-service:8001/health
docker-compose exec ai-analyzer curl -f http://email-webhook:8001/health
```

**Checklist**:
- [ ] Services can reach each other
- [ ] No network isolation issues

---

## Step 2: Database Migrations

### 2.1 Run Health Monitoring Migrations
```bash
# Check current migrations
make db-shell
SELECT id, description, executed_at FROM schema_migrations ORDER BY id DESC;

# Run migrations
python database/scripts/run_migrations.py

# Verify new tables created
make db-shell
\dt health_checks
\dt error_logs
\dt alert_logs
\dt alert_state
```

**Checklist**:
- [ ] Migrations 012 and 013 ran successfully
- [ ] health_checks table exists with correct schema
- [ ] error_logs table exists with correct schema
- [ ] alert_logs table exists with correct schema
- [ ] alert_state table exists with correct schema
- [ ] All indexes created

### 2.2 Verify Table Structure
```bash
make db-shell

# Check health_checks table
\d+ health_checks

# Check error_logs table
\d+ error_logs

# Check alert_logs table
\d+ alert_logs

# Check alert_state table
\d+ alert_state

# Verify indexes
\di+ *health* *error* *alert*
```

**Checklist**:
- [ ] health_checks: id (UUID PK), service_name (VARCHAR), status (VARCHAR), check_timestamp, check_duration_ms, details_json, created_at
- [ ] error_logs: id (UUID PK), error_timestamp, service_name, error_type, severity, message, context_json, source_report_id, stack_trace, correlation_id, created_at
- [ ] alert_logs: id (UUID PK), error_id (FK), alert_timestamp, alert_type, recipient, delivery_status, sent_at, delivery_latency_ms, created_at
- [ ] alert_state: id (UUID PK), service_name, error_type, last_alert_sent_at, consecutive_failure_count, alert_suppressed_until, created_at, updated_at
- [ ] Unique constraint on alert_state(service_name, error_type)
- [ ] Foreign key constraint alert_logs.error_id → error_logs.id with ON DELETE CASCADE

### 2.3 Test Database Operations
```bash
make db-shell

-- Test insert into health_checks (append-only)
INSERT INTO health_checks (id, service_name, status, check_timestamp, check_duration_ms, details_json, created_at)
VALUES (gen_random_uuid(), 'test-service', 'up', NOW(), 100, '{}', NOW());

-- Verify insert
SELECT COUNT(*) FROM health_checks;

-- Test that UPDATE fails (append-only)
-- This should fail with permission error or trigger error
UPDATE health_checks SET status = 'down' WHERE service_name = 'test-service';

-- Clean up test data
DELETE FROM health_checks WHERE service_name = 'test-service';

\q
```

**Checklist**:
- [ ] Can insert into health_checks
- [ ] UPDATE prevented or fails as expected
- [ ] Test data cleaned up

---

## Step 3: Environment Configuration

### 3.1 Verify .env File
```bash
# Copy from example if not exists
[ -f .env ] || cp .env.example .env

# Verify critical variables are set
grep -E "ALERT_EMAIL_ADMIN|POSTGRES_PASSWORD|TRADING_USER_PASSWORD|ALERT_BATCH_WINDOW" .env

# Should output:
# ALERT_EMAIL_ADMIN=admin@example.com (or actual email)
# POSTGRES_PASSWORD=... (should not be empty)
# TRADING_USER_PASSWORD=... (should not be empty)
# ALERT_BATCH_WINDOW=60
```

**Checklist**:
- [ ] .env file exists
- [ ] ALERT_EMAIL_ADMIN is set
- [ ] POSTGRES_PASSWORD is set
- [ ] TRADING_USER_PASSWORD is set
- [ ] SMTP_HOST, SMTP_USER, SMTP_PASSWORD configured
- [ ] HEALTH_CHECK_INTERVAL set (default 60)
- [ ] HEALTH_CHECK_TIMEOUT set (default 5)
- [ ] ERROR_LOG_RETENTION_DAYS set (default 30)
- [ ] HEALTH_CHECK_RETENTION_DAYS set (default 7)

### 3.2 Verify Service URLs
```bash
# Check service URLs are correct in docker-compose.yml
grep -A 10 "health-monitoring:" docker-compose.yml | grep "URL"

# Should show:
# EMAIL_WEBHOOK_URL=http://email-webhook:8001
# PLAYWRIGHT_SCRAPER_URL=http://playwright-scraper:8002
# AI_ANALYZER_URL=http://ai-analyzer:8000
# NOTIFICATION_SERVICE_URL=http://notification-service:8001
# N8N_URL=http://n8n:5678
```

**Checklist**:
- [ ] All service URLs configured correctly
- [ ] URLs use Docker container names (not localhost)
- [ ] Ports match docker-compose service definitions

---

## Step 4: Build Health Monitoring Service

### 4.1 Build Docker Image
```bash
# Build health-monitoring image
docker-compose build health-monitoring

# Verify build succeeded
docker images | grep trading-health-monitoring
```

**Checklist**:
- [ ] Docker build completed without errors
- [ ] Image appears in docker images list
- [ ] Image size is reasonable (< 500MB)

### 4.2 Verify Docker Image
```bash
# Inspect image
docker inspect trading-health-monitoring:latest | grep -E "Architecture|Os"

# Check that Python 3.11 is installed
docker run trading-health-monitoring:latest python --version
```

**Checklist**:
- [ ] Image runs without errors
- [ ] Python version correct (3.11+)
- [ ] Required dependencies present

---

## Step 5: Start Health Monitoring Service

### 5.1 Start Service Container
```bash
# Start only health-monitoring (or start all services)
docker-compose up -d health-monitoring

# Wait for service to become healthy
sleep 5

# Check status
docker-compose ps health-monitoring

# Should show:
# trading-health-monitoring ... Up ... (healthy)
```

**Checklist**:
- [ ] Service container started
- [ ] Container is running (status "Up")
- [ ] Container becomes healthy within 60 seconds
- [ ] No errors in container startup logs

### 5.2 Verify Service Health
```bash
# Test health endpoint
curl -f http://localhost:8003/health

# Should respond:
# {
#   "status": "ok",
#   "service": "health-monitoring",
#   "timestamp": "2024-12-03T..."
# }
```

**Checklist**:
- [ ] GET /health responds with 200
- [ ] Response contains "status": "ok"
- [ ] Service is accessible on port 8003

### 5.3 Check Service Logs
```bash
# View recent logs
docker-compose logs health-monitoring | tail -50

# Should show:
# - Database pool initialized
# - Health check service initialized
# - Services started successfully
```

**Checklist**:
- [ ] Database connection pool initialized
- [ ] Health check service initialized
- [ ] Background tasks started
- [ ] No error messages in startup logs

---

## Step 6: Health Check Verification

### 6.1 Test Health Aggregation Endpoint
```bash
# Get aggregate health status
curl http://localhost:8003/api/v1/health/status

# Should respond with JSON:
# {
#   "timestamp": "2024-12-03T...",
#   "overall_status": "healthy",
#   "services": [
#     {"service_name": "email-webhook", "status": "up", ...},
#     {"service_name": "playwright-scraper", "status": "up", ...},
#     ...
#   ]
# }
```

**Checklist**:
- [ ] Endpoint responds with 200
- [ ] overall_status is in ["healthy", "degraded", "unhealthy"]
- [ ] All 5 services listed
- [ ] Each service has status, check_timestamp, check_duration_ms

### 6.2 Test Error Retrieval Endpoint
```bash
# Get recent errors
curl 'http://localhost:8003/api/v1/health/errors?severity=CRITICAL&hours=24'

# Should respond with JSON:
# {
#   "timestamp": "2024-12-03T...",
#   "count": 0,
#   "errors": []
# }
# (Empty errors list is OK on fresh deployment)
```

**Checklist**:
- [ ] Endpoint responds with 200
- [ ] Response contains timestamp and count
- [ ] Errors array exists (may be empty)

### 6.3 Test Manual Health Check Trigger
```bash
# Trigger health check for specific service
curl -X POST http://localhost:8003/api/v1/health/check/ai-analyzer

# Should respond with JSON:
# {
#   "service_name": "ai-analyzer",
#   "status": "up",
#   "check_timestamp": "2024-12-03T...",
#   "check_duration_ms": 120,
#   ...
# }
```

**Checklist**:
- [ ] Endpoint responds with 200
- [ ] Service status is "up", "down", or "degraded"
- [ ] check_duration_ms is positive and < 5000

---

## Step 7: Alert Configuration

### 7.1 Test Email Configuration
```bash
# Verify SMTP settings in notification-service
curl http://localhost:8001/health

# Should respond with notification service health
```

**Checklist**:
- [ ] Notification service is healthy
- [ ] SMTP credentials are configured
- [ ] Email provider accessible

### 7.2 Test Alert Email Delivery
```bash
# Check if notification service can send test email
# (Method depends on notification service implementation)
# Typically via: POST /api/v1/notify with test template

curl -X POST http://localhost:8001/api/v1/notify \
  -H "Content-Type: application/json" \
  -d '{
    "template_type": "test_alert",
    "recipient": "YOUR_EMAIL@example.com",
    "context": {"test": true}
  }'
```

**Checklist**:
- [ ] Test email sent successfully
- [ ] Email received in ALERT_EMAIL_ADMIN inbox
- [ ] Email formatting looks correct

### 7.3 Verify Alert Batch Settings
```bash
# Check configured alert batching
grep -E "ALERT_BATCH_WINDOW|ALERT_AUTO_RESOLVE" .env

# Should show:
# ALERT_BATCH_WINDOW=60
# ALERT_AUTO_RESOLVE_WINDOW=5
```

**Checklist**:
- [ ] ALERT_BATCH_WINDOW set correctly
- [ ] ALERT_AUTO_RESOLVE_WINDOW set correctly
- [ ] Alert state table empty (fresh deployment)

---

## Step 8: Database Verification

### 8.1 Verify Health Check Storage
```bash
make db-shell

-- Check health checks are being stored
SELECT COUNT(*) as health_check_count FROM health_checks;

-- Should show count > 0 after health checks have run

-- Check latest health checks
SELECT service_name, status, check_timestamp
FROM health_checks
ORDER BY check_timestamp DESC
LIMIT 10;

-- Should show recent checks for all 5 services
```

**Checklist**:
- [ ] Health checks table has data
- [ ] All 5 services represented
- [ ] Timestamps are recent (last check within 2 minutes)
- [ ] Status values are "up" or "degraded" or "down"

### 8.2 Verify Alert State Table
```bash
make db-shell

-- Check alert state (should be empty or minimal on fresh deployment)
SELECT COUNT(*) as alert_state_count FROM alert_state;

-- Check indexes exist
\di+ *alert_state*

-- Should show indexes on: (service_name, error_type), alert_suppressed_until, updated_at
```

**Checklist**:
- [ ] alert_state table exists
- [ ] Indexes created on required columns
- [ ] Unique constraint on (service_name, error_type) exists

### 8.3 Verify Retention Policies
```bash
make db-shell

-- Check error log retention setting (manually, since no errors yet)
-- Verify health check retention

-- Create test error data (optional)
INSERT INTO error_logs
  (id, error_timestamp, service_name, error_type, severity, message, created_at)
VALUES
  (gen_random_uuid(), NOW() - INTERVAL '31 days', 'test', 'test_error', 'WARNING', 'test', NOW() - INTERVAL '31 days');

-- Verify old data would be deleted by cleanup job
SELECT COUNT(*) FROM error_logs WHERE created_at < NOW() - INTERVAL '30 days';

-- Clean up
DELETE FROM error_logs WHERE service_name = 'test';

\q
```

**Checklist**:
- [ ] error_logs table exists with correct schema
- [ ] health_checks table exists with correct schema
- [ ] Cleanup queries would identify old data correctly
- [ ] Test data cleaned up

---

## Step 9: Integration Testing

### 9.1 Run Health Monitoring Tests
```bash
# Run all health monitoring tests
cd services/health-monitoring && pytest tests/ -v

# Run specific test suites
pytest tests/test_health_checks.py -v
pytest tests/test_n8n_integration.py -v
pytest tests/test_integration.py -v
```

**Checklist**:
- [ ] All tests pass (or document expected failures)
- [ ] No database connection errors
- [ ] N8N integration tests pass
- [ ] Integration tests pass

### 9.2 Test End-to-End Workflow
```bash
# Simulate an error in one of the services
# (This depends on service implementation)

# Then verify:
# 1. Error appears in error_logs
curl 'http://localhost:8003/api/v1/health/errors?severity=ERROR&hours=1'

# 2. Check health aggregation still works
curl http://localhost:8003/api/v1/health/status

# 3. Verify alert would be generated (if CRITICAL)
# Check alert_state table
make db-shell
SELECT * FROM alert_state;
```

**Checklist**:
- [ ] Errors are logged correctly
- [ ] Health checks continue running despite errors
- [ ] Alert state updated for critical errors
- [ ] API endpoints remain responsive

### 9.3 Performance Validation
```bash
# Measure health status response time
time curl http://localhost:8003/api/v1/health/status

# Should complete in < 2 seconds

# Measure error retrieval performance
time curl 'http://localhost:8003/api/v1/health/errors?limit=100'

# Should complete in < 500ms

# Check database query performance
make db-shell
EXPLAIN ANALYZE SELECT COUNT(*) FROM error_logs WHERE severity = 'CRITICAL';
EXPLAIN ANALYZE SELECT * FROM health_checks WHERE check_timestamp > NOW() - INTERVAL '24 hours';
```

**Checklist**:
- [ ] Health status endpoint < 2 seconds
- [ ] Error retrieval endpoint < 500ms
- [ ] Database queries use indexes
- [ ] No full table scans in EXPLAIN plans

---

## Step 10: N8N Integration Setup

### 10.1 Configure N8N Environment Variables
```bash
# Access N8N UI: http://localhost:5678

# Navigate to: Settings → Environment Variables
# Add these variables:
# - HEALTH_MONITORING_URL=http://health-monitoring:8003
# - ALERT_EMAIL_ADMIN=admin@example.com
# - NOTIFICATION_SERVICE_URL=http://notification-service:8001
```

**Checklist**:
- [ ] N8N UI accessible
- [ ] Environment variables added
- [ ] Variables visible in N8N workflows

### 10.2 Create Health Status Monitor Workflow
```bash
# In N8N UI:
# 1. Create new workflow
# 2. Add Scheduler node (every 5 minutes)
# 3. Add HTTP Request node:
#    - URL: {{ $env.HEALTH_MONITORING_URL }}/api/v1/health/status
#    - Method: GET
# 4. Add Filter node: $json.overall_status !== "healthy"
# 5. Add Email node (if degraded)
# 6. Save and activate workflow
```

**Checklist**:
- [ ] Workflow created
- [ ] HTTP node calls health status correctly
- [ ] Filter logic correct
- [ ] Workflow tested successfully
- [ ] Workflow activated (schedule enabled)

### 10.3 Create Error Alert Workflow
```bash
# In N8N UI:
# 1. Create new workflow
# 2. Add Scheduler node (every 1 minute)
# 3. Add HTTP Request node:
#    - URL: {{ $env.HEALTH_MONITORING_URL }}/api/v1/health/errors?severity=CRITICAL&hours=1
#    - Method: GET
# 4. Add Filter node: $json.errors.length > 0
# 5. Add Email node with error table formatting
# 6. Save and activate workflow
```

**Checklist**:
- [ ] Error alert workflow created
- [ ] Calls health errors endpoint correctly
- [ ] Email formatting working
- [ ] Workflow tested
- [ ] Workflow activated

---

## Step 11: Documentation Review

### 11.1 Verify Documentation Files
```bash
# Check that all documentation exists
ls -l HEALTH_MONITORING.md
ls -l HEALTH_MONITORING_DEPLOYMENT.md
ls -l CLAUDE.md
ls -l refs/n8n-workflows/README.md
```

**Checklist**:
- [ ] HEALTH_MONITORING.md exists (operator manual)
- [ ] HEALTH_MONITORING_DEPLOYMENT.md exists (this file)
- [ ] CLAUDE.md updated with health monitoring section
- [ ] N8N workflow documentation exists
- [ ] All documentation links to each other

### 11.2 Review Configuration Examples
```bash
# Verify .env.example has all health monitoring variables
grep -c "HEALTH_\|ALERT_\|ERROR_LOG_RETENTION" .env.example

# Should show at least 6 matches
```

**Checklist**:
- [ ] .env.example has all required variables
- [ ] Variables have comments explaining purpose
- [ ] Default values documented
- [ ] Examples provided

---

## Step 12: Backup & Recovery

### 12.1 Create Initial Backup
```bash
# Backup database
make db-backup

# Should create file like: backups/trading_reports_backup_2024-12-03.sql
ls -lah backups/ | tail -1
```

**Checklist**:
- [ ] Database backup created
- [ ] Backup file size > 1MB (contains schema and data)
- [ ] Backup stored in accessible location
- [ ] Backup filename includes timestamp

### 12.2 Test Backup Restore
```bash
# List available backups
ls -l backups/

# Verify backup can be restored (optional but recommended)
# DO NOT restore in production without planning
# Just verify the backup file is readable:
file backups/trading_reports_backup*.sql
```

**Checklist**:
- [ ] Backup files exist
- [ ] Backups are readable (not corrupted)
- [ ] Restore procedure documented
- [ ] Team knows how to restore from backup

---

## Step 13: Post-Deployment Monitoring

### 13.1 Monitor First 24 Hours
```bash
# Check health status every hour
watch -n 3600 'curl -s http://localhost:8003/api/v1/health/status | jq .overall_status'

# Monitor logs for errors
docker-compose logs -f health-monitoring | grep -E "ERROR|CRITICAL"

# Check database growth
make db-shell
SELECT pg_size_pretty(pg_database_size('trading_reports'));
```

**Checklist**:
- [ ] Health status remains "healthy" or "degraded"
- [ ] No ERROR or CRITICAL in startup logs
- [ ] Database size growing at expected rate (not explosive)
- [ ] Health checks running on schedule (visible in logs)

### 13.2 First Week Checks
```bash
# Check error logs for patterns
curl 'http://localhost:8003/api/v1/health/errors?hours=168' | jq '.errors | length'

# Review alert state
make db-shell
SELECT service_name, error_type, consecutive_failure_count, last_alert_sent_at
FROM alert_state
WHERE consecutive_failure_count > 0;

# Check alert delivery success rate
SELECT delivery_status, COUNT(*) FROM alert_logs GROUP BY delivery_status;
```

**Checklist**:
- [ ] Error logs show normal service errors (not unexpected)
- [ ] Alert state tracks errors correctly
- [ ] Alerts are being delivered (success rate > 95%)
- [ ] No alert spam (check consecutive_failure_count)

### 13.3 First Month Operations
```bash
# Verify cleanup jobs work
# Check for data older than retention window
make db-shell
SELECT COUNT(*) FROM error_logs WHERE created_at < NOW() - INTERVAL '30 days';
SELECT COUNT(*) FROM health_checks WHERE created_at < NOW() - INTERVAL '7 days';

# These should be 0 if cleanup job ran successfully
```

**Checklist**:
- [ ] Cleanup jobs executed successfully
- [ ] No old data beyond retention window
- [ ] Database size stable
- [ ] Performance not degraded

---

## Rollback Procedure

If deployment fails, follow these steps:

### 13.1 Stop Health Monitoring Service
```bash
docker-compose down health-monitoring
```

### 13.2 Revert Database (if migrations failed)
```bash
# Restore from backup
make db-restore
# Select the backup from before migrations
```

### 13.3 Remove Configuration
```bash
# Remove health monitoring from docker-compose (temporarily)
# Remove health monitoring environment variables from .env
```

### 13.4 Restart Other Services
```bash
docker-compose up -d
```

---

## Success Criteria

The deployment is considered successful when:

- [x] All database migrations completed without errors
- [x] health-monitoring service running and healthy
- [x] All 5 services report health correctly
- [x] API endpoints respond in < 2 seconds
- [x] Errors logged to database within 1 second of occurrence
- [x] Test alerts delivered to ALERT_EMAIL_ADMIN
- [x] No data loss or corruption
- [x] All tests passing
- [x] Documentation reviewed and accessible
- [x] Team trained on monitoring and troubleshooting

---

## Post-Deployment Handoff

After successful deployment, document:

1. **Who deployed** (name, date, time)
2. **Environment** (development, staging, production)
3. **Current status** (all checks passed)
4. **Contact for issues** (who to contact if something breaks)
5. **Monitoring dashboard** (link to N8N dashboards)
6. **Backup location** (where backups are stored)
7. **Next steps** (ongoing maintenance, scaling)

---

**Deployment Completed**: _____________________
**Deployed By**: _____________________________
**Date**: ___________________________________
**Environment**: ____________________________
**Verified By**: ____________________________
