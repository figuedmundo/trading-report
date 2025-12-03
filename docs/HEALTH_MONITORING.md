# Health Monitoring & Error Logging Operator Manual

## Overview

The Health Monitoring system provides real-time visibility into the health and availability of all trading report microservices. It continuously monitors service availability, logs errors with full context, generates alerts on critical failures, and maintains a complete audit trail for compliance.

**Key Capabilities:**
- Real-time health checks for all 5 microservices (email-webhook, playwright-scraper, ai-analyzer, notification-service, n8n)
- Centralized error logging with severity classification (CRITICAL, ERROR, WARNING)
- Intelligent alert generation with spam prevention and automatic batching
- 30-day error retention and 7-day health history for compliance
- Email alerts on critical failures
- N8N workflow integration for monitoring dashboards

## System Architecture

### Service Dependencies

```
Health Monitoring Service (Port 8003)
├── Database: PostgreSQL
│   ├── health_checks table (append-only)
│   ├── error_logs table (append-only)
│   ├── alert_logs table
│   └── alert_state table (tracks batching)
│
├── Monitored Services:
│   ├── Email Webhook (Port 8001)
│   ├── Playwright Scraper (Port 8002)
│   ├── AI Analyzer (Port 8000)
│   ├── Notification Service (Port 8001)
│   └── N8N (Port 5678)
│
└── External Integration:
    └── Notification Service (for alert delivery)
```

### Health Check Architecture

Each service is monitored on a 60-second interval via the `/health` endpoint. The health monitoring service:
1. Calls the health endpoint of each service
2. Measures response time (must complete in < 5 seconds)
3. Stores result in `health_checks` table
4. Provides aggregated status via `/api/v1/health/status`

### Error Logging Flow

```
1. Error occurs in microservice
   ↓
2. Service logs error with ErrorLogger class
   ↓
3. Error stored in error_logs table (with full context)
   ↓
4. If CRITICAL severity:
   ├─ AlertService checks for batching
   ├─ Determines if alert should be sent (not already sent in last 5 minutes)
   └─ Sends alert via notification service to ALERT_EMAIL_ADMIN
   ↓
5. Alert logged to alert_logs table with delivery status
```

## Configuration

### Environment Variables

All configuration is done via environment variables. Copy `.env.example` to `.env` and set these values:

```bash
# Health Monitoring Service Port
SERVICE_PORT=8003

# Logging Level
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Database Connection
DATABASE_URL=postgresql://trading_user:${TRADING_USER_PASSWORD}@postgres:5432/trading_reports

# Health Check Configuration
HEALTH_CHECK_INTERVAL=60              # Seconds between health checks (default: 60)
HEALTH_CHECK_TIMEOUT=5                # Maximum seconds to wait for service response (default: 5)
ENABLE_HEALTH_MONITORING=true         # Enable/disable health monitoring (default: true)

# Alert Configuration
ALERT_EMAIL_ADMIN=admin@example.com   # Email address for critical alerts (REQUIRED)
ALERT_BATCH_WINDOW=60                 # Minutes to batch consecutive failures (default: 60)
ALERT_AUTO_RESOLVE_WINDOW=5           # Minutes to suppress re-alerts if resolved (default: 5)

# Data Retention
ERROR_LOG_RETENTION_DAYS=30           # Days to keep error logs (default: 30)
HEALTH_CHECK_RETENTION_DAYS=7         # Days to keep health check history (default: 7)

# Service URLs (for health checks)
EMAIL_WEBHOOK_URL=http://email-webhook:8001
PLAYWRIGHT_SCRAPER_URL=http://playwright-scraper:8002
AI_ANALYZER_URL=http://ai-analyzer:8000
NOTIFICATION_SERVICE_URL=http://notification-service:8001
N8N_URL=http://n8n:5678
```

### Alert Configuration

#### Alert Email Setup

The `ALERT_EMAIL_ADMIN` variable specifies who receives critical alerts. Ensure:

1. Email address is valid
2. Notification service has SMTP configured (see notification service documentation)
3. Test alert delivery: Check alert_logs table for successful delivery

#### Batching Strategy

The system prevents alert spam by batching consecutive failures:

- **5-minute window**: Identical errors within 5 minutes → suppress re-alert
- **60-minute window**: Multiple errors of same type from same service → batch into single alert with `consecutive_failure_count` field
- **Auto-resolution**: If no errors occur for 5 minutes → alert state resets

Example:
```
Time   Event                                                Alert Sent?
10:00  First login_failed error (playwright-scraper)       YES (alert 1)
10:02  Second login_failed error                            NO (within 5 min)
10:05  Third login_failed error                             NO (batched)
10:07  Fourth login_failed error                            NO (batched)
       Alert 1 shows: "consecutive_failure_count": 4
10:61  If no more errors since 10:05 (5+ min window)       Alert state reset
11:00  New login_failed error (after reset)                YES (alert 2)
```

## API Reference

### Health Check Endpoints

#### GET /health
Minimal health check for Docker healthcheck. Fast response.

```bash
curl http://localhost:8003/health
```

Response:
```json
{
  "status": "ok",
  "service": "health-monitoring",
  "timestamp": "2024-12-03T14:30:45.123456+00:00"
}
```

#### GET /api/v1/health/status
Get aggregate health status of all 5 services.

```bash
curl http://localhost:8003/api/v1/health/status
```

Response:
```json
{
  "timestamp": "2024-12-03T14:30:45.123456+00:00",
  "overall_status": "healthy",
  "services": [
    {
      "service_name": "email-webhook",
      "status": "up",
      "check_timestamp": "2024-12-03T14:30:40.123456+00:00",
      "check_duration_ms": 120,
      "details": {"database": "ok"}
    },
    {
      "service_name": "playwright-scraper",
      "status": "up",
      "check_timestamp": "2024-12-03T14:30:40.123456+00:00",
      "check_duration_ms": 150,
      "details": {"database": "ok", "playwright": "browser_available"}
    },
    {
      "service_name": "ai-analyzer",
      "status": "degraded",
      "check_timestamp": "2024-12-03T14:30:40.123456+00:00",
      "check_duration_ms": 4800,
      "details": {"database": "slow_query", "api_key": "configured"}
    },
    {
      "service_name": "notification-service",
      "status": "up",
      "check_timestamp": "2024-12-03T14:30:40.123456+00:00",
      "check_duration_ms": 110,
      "details": {"database": "ok", "smtp": "ok"}
    },
    {
      "service_name": "n8n",
      "status": "up",
      "check_timestamp": "2024-12-03T14:30:40.123456+00:00",
      "check_duration_ms": 90,
      "details": {}
    }
  ]
}
```

**Status Values:**
- `"healthy"`: All services up
- `"degraded"`: Some services up, some services slow (> 2 seconds)
- `"unhealthy"`: One or more services down

#### GET /api/v1/health/errors
Retrieve recent errors with filtering.

```bash
# Get all CRITICAL errors in last 24 hours
curl 'http://localhost:8003/api/v1/health/errors?severity=CRITICAL&limit=20'

# Get all errors from specific service in last 48 hours
curl 'http://localhost:8003/api/v1/health/errors?service=ai-analyzer&hours=48'

# Get ERROR and WARNING severity combined
curl 'http://localhost:8003/api/v1/health/errors?severity=ERROR&limit=50'
```

Query Parameters:
- `severity` (optional): `CRITICAL`, `ERROR`, or `WARNING`
- `service` (optional): Service name (email-webhook, playwright-scraper, ai-analyzer, notification-service, n8n)
- `hours` (optional, default: 24): Time window in hours
- `limit` (optional, default: 10): Maximum number of errors to return

Response:
```json
{
  "timestamp": "2024-12-03T14:30:45.123456+00:00",
  "count": 3,
  "errors": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "error_timestamp": "2024-12-03T14:15:30.123456+00:00",
      "service_name": "playwright-scraper",
      "error_type": "login_failed",
      "severity": "CRITICAL",
      "message": "Failed to login to trading portal after 3 retries",
      "context_json": {
        "portal_name": "example.com",
        "retry_count": 3,
        "http_status": 401
      },
      "source_report_id": "550e8400-e29b-41d4-a716-446655440002",
      "stack_trace": null,
      "correlation_id": "req-20241203-abc123def456"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "error_timestamp": "2024-12-03T14:10:15.123456+00:00",
      "service_name": "ai-analyzer",
      "error_type": "api_timeout",
      "severity": "CRITICAL",
      "message": "Claude API request timeout after 30 seconds",
      "context_json": {
        "model": "claude-3-sonnet",
        "elapsed_seconds": 30,
        "expected_timeout": 30
      },
      "source_report_id": "550e8400-e29b-41d4-a716-446655440004",
      "stack_trace": "Traceback (most recent call last):\n  File \"/app/src/services/analyzer.py\", line 45, in analyze\n    ...",
      "correlation_id": "req-20241203-def789ghi012"
    }
  ]
}
```

#### POST /api/v1/health/check/{service}
Trigger a manual health check for a specific service.

```bash
# Check email-webhook service
curl -X POST http://localhost:8003/api/v1/health/check/email-webhook

# Check ai-analyzer service
curl -X POST http://localhost:8003/api/v1/health/check/ai-analyzer
```

Valid Service Names:
- `email-webhook`
- `playwright-scraper`
- `ai-analyzer`
- `notification-service`
- `n8n`

Response:
```json
{
  "service_name": "email-webhook",
  "status": "up",
  "check_timestamp": "2024-12-03T14:30:45.123456+00:00",
  "check_duration_ms": 120,
  "details": {"database": "ok"}
}
```

HTTP Status Codes:
- `200`: Health check completed successfully
- `400`: Invalid service name
- `408`: Health check timeout (service didn't respond within 5 seconds)
- `500`: Internal server error

## Health Check Details

### Email Webhook Service
Checks:
- HTTP connectivity to /health endpoint
- Database connection
- Webhook endpoint accessibility
- Security event logging capability

### Playwright Scraper Service
Checks:
- HTTP connectivity to /health endpoint
- Database connection
- Playwright browser availability
- Portal credential storage accessibility

### AI Analyzer Service
Checks:
- HTTP connectivity to /health endpoint
- Database connection
- AI API key configuration and validity
- External API connectivity (Claude API or Groq)

### Notification Service
Checks:
- HTTP connectivity to /health endpoint
- Database connection
- SMTP server connectivity (email sending capability)
- Telegram API reachability (if configured)

### N8N Service
Checks:
- HTTP connectivity to N8N web interface
- PostgreSQL database connectivity from N8N perspective
- Workflow engine availability

## Error Severity Levels

### CRITICAL
System-blocking errors that prevent service operation. Require immediate attention.

**Examples:**
- Failed login to trading portal (cannot extract reports)
- Database connection failure (no data persistence)
- Required API key missing or expired (cannot process)
- Webhook signature validation failure (cannot receive events)
- Service failed to start (complete unavailability)

**Alert Action:** Email alert sent immediately to ALERT_EMAIL_ADMIN

### ERROR
Single-report failures that affect specific processing but don't block the system.

**Examples:**
- Content extraction timeout (report processing failed)
- Analysis API failure (cannot analyze specific report)
- Email send failure (notification delivery failed)
- Telegram API error (telegram delivery failed)
- Specific report processing failed mid-pipeline

**Alert Action:** No automatic alert, but visible in error logs for investigation

### WARNING
Non-blocking issues for monitoring but don't require immediate action.

**Examples:**
- Slow response time (> 5 seconds but < timeout)
- Rate limit triggered (API temporarily blocked)
- Retry attempted (transient error)
- Transient API error (will retry automatically)
- SSL certificate warning (connection still works)

**Alert Action:** No alert, logged for trending and analysis

## Troubleshooting

### No Errors Appearing in API

1. **Check if health monitoring service is running:**
   ```bash
   docker-compose ps | grep health-monitoring
   curl http://localhost:8003/health
   ```

2. **Verify database connectivity:**
   ```bash
   make db-shell
   SELECT COUNT(*) FROM error_logs;
   ```

3. **Check logs:**
   ```bash
   make logs-service SERVICE=health-monitoring
   ```

### Alerts Not Sending

1. **Verify ALERT_EMAIL_ADMIN is configured:**
   ```bash
   grep ALERT_EMAIL_ADMIN .env
   ```

2. **Check notification service is healthy:**
   ```bash
   curl http://localhost:8001/health
   ```

3. **Check alert delivery attempts in database:**
   ```bash
   make db-shell
   SELECT * FROM alert_logs ORDER BY created_at DESC LIMIT 10;
   ```

4. **Review alert state for service:**
   ```bash
   make db-shell
   SELECT * FROM alert_state WHERE service_name = 'email-webhook';
   ```

### Health Checks Timing Out

1. **Check service is running:**
   ```bash
   docker-compose ps
   ```

2. **Verify service health endpoint:**
   ```bash
   curl http://localhost:8001/health        # email-webhook
   curl http://localhost:8002/health        # playwright-scraper
   curl http://localhost:8000/health        # ai-analyzer
   curl http://localhost:8001/health        # notification-service (different port)
   curl http://localhost:5678               # n8n
   ```

3. **Increase timeout if services are legitimately slow:**
   ```bash
   # In .env:
   HEALTH_CHECK_TIMEOUT=10  # Increase from default 5
   ```

### High Error Volume / Alert Spam

1. **Check alert batching settings:**
   ```bash
   # Increase batching window to reduce alerts
   ALERT_BATCH_WINDOW=120  # 2 hours instead of 60
   ALERT_AUTO_RESOLVE_WINDOW=10  # 10 minutes instead of 5
   ```

2. **Monitor alert_state table for recurring errors:**
   ```bash
   make db-shell
   SELECT service_name, error_type, consecutive_failure_count,
          last_alert_sent_at, alert_suppressed_until
   FROM alert_state
   WHERE consecutive_failure_count > 5;
   ```

3. **Check root cause of error:**
   ```bash
   curl 'http://localhost:8003/api/v1/health/errors?severity=CRITICAL&hours=1'
   ```

## N8N Integration

Health monitoring integrates with N8N for workflow-based monitoring and alerting:

### Health Status Dashboard Workflow

1. **Setup Scheduler Node**: Run every 5 minutes
2. **Add HTTP Request Node**:
   - URL: `{{ $env.HEALTH_MONITORING_URL }}/api/v1/health/status`
   - Method: GET
3. **Add Filter Node**: Check if overall_status != "healthy"
4. **Add Email Node**: Send alert if services degraded
5. **Add Database Node**: Log workflow execution

### Error Alert Workflow

1. **Setup Scheduler Node**: Run every minute
2. **Add HTTP Request Node**:
   - URL: `{{ $env.HEALTH_MONITORING_URL }}/api/v1/health/errors?severity=CRITICAL&hours=1`
   - Method: GET
3. **Add Filter Node**: Check for new errors (compare timestamps)
4. **Add Email Node**: Send alert if new CRITICAL errors found
5. **Add Function Node**: Format error details into readable email

### Accessing in N8N UI

1. Navigate to http://localhost:5678
2. Go to Workflows
3. Create new workflow with HTTP Request nodes
4. Set environment variables in N8N:
   ```
   HEALTH_MONITORING_URL=http://health-monitoring:8003
   ```

## Monitoring Best Practices

### Daily Operations

1. **Check overall status:**
   ```bash
   curl http://localhost:8003/api/v1/health/status | jq '.overall_status'
   ```

2. **Review recent errors:**
   ```bash
   curl 'http://localhost:8003/api/v1/health/errors?severity=CRITICAL&hours=24'
   ```

3. **Monitor alert_state for stuck errors:**
   ```bash
   make db-shell
   SELECT * FROM alert_state
   WHERE consecutive_failure_count > 10
   OR alert_suppressed_until > NOW();
   ```

### Weekly Review

1. **Analyze error trends:**
   ```bash
   make db-shell
   SELECT DATE(error_timestamp) as date, service_name, severity, COUNT(*) as count
   FROM error_logs
   WHERE error_timestamp > NOW() - INTERVAL '7 days'
   GROUP BY DATE(error_timestamp), service_name, severity
   ORDER BY date DESC;
   ```

2. **Check alert delivery success rate:**
   ```bash
   make db-shell
   SELECT delivery_status, COUNT(*) as count
   FROM alert_logs
   WHERE alert_timestamp > NOW() - INTERVAL '7 days'
   GROUP BY delivery_status;
   ```

3. **Review service uptime:**
   ```bash
   make db-shell
   SELECT service_name,
       COUNT(CASE WHEN status = 'up' THEN 1 END)::float / COUNT(*) * 100 as uptime_pct
   FROM health_checks
   WHERE check_timestamp > NOW() - INTERVAL '7 days'
   GROUP BY service_name;
   ```

### Monthly Maintenance

1. **Archive old error logs:**
   ```bash
   curl -X POST http://localhost:8003/api/v1/health/archive/error_logs \
     -H "Content-Type: application/json" \
     -d '{"before_date": "2024-11-03"}'
   ```

2. **Verify retention policies:**
   ```bash
   make db-shell
   -- Check error logs older than 30 days exist
   SELECT COUNT(*) FROM error_logs
   WHERE created_at < NOW() - INTERVAL '30 days';

   -- Check health checks older than 7 days exist
   SELECT COUNT(*) FROM health_checks
   WHERE created_at < NOW() - INTERVAL '7 days';
   ```

3. **Review alert state for stale entries:**
   ```bash
   make db-shell
   SELECT * FROM alert_state
   WHERE last_alert_sent_at < NOW() - INTERVAL '30 days'
   AND consecutive_failure_count > 0;
   ```

## Support & Escalation

### When to Escalate

1. **Multiple services down** (overall_status = "unhealthy"):
   - Check docker-compose logs: `make logs`
   - Restart all services: `make dev-build`
   - Check database connectivity: `make db-shell`

2. **Database connection failures**:
   - Verify PostgreSQL is running: `docker-compose ps postgres`
   - Check database size: `make db-shell` → `\l`
   - Review database logs for errors

3. **Notification service failures**:
   - Verify SMTP/Telegram credentials
   - Check notification-service logs: `make logs-service SERVICE=notification-service`
   - Test manual email send via service API

## Database Schema Reference

### health_checks table
Append-only log of all health checks for trending and audit.

```sql
SELECT * FROM health_checks
WHERE service_name = 'ai-analyzer'
AND check_timestamp > NOW() - INTERVAL '24 hours'
ORDER BY check_timestamp DESC;
```

### error_logs table
Append-only log of all errors with full context for debugging.

```sql
SELECT * FROM error_logs
WHERE severity = 'CRITICAL'
AND error_timestamp > NOW() - INTERVAL '48 hours'
ORDER BY error_timestamp DESC;
```

### alert_logs table
Audit trail of all alert delivery attempts.

```sql
SELECT * FROM alert_logs
WHERE delivery_status = 'failed'
ORDER BY alert_timestamp DESC;
```

### alert_state table
Current state of alert batching (only table with UPDATE operations).

```sql
SELECT * FROM alert_state
WHERE service_name = 'playwright-scraper';
```

## Appendix: Common Error Types

### Login Errors
```json
{
  "error_type": "login_failed",
  "severity": "CRITICAL",
  "context_json": {
    "portal_name": "example.com",
    "retry_count": 3,
    "http_status": 401
  }
}
```

### Database Errors
```json
{
  "error_type": "database_connection_failed",
  "severity": "CRITICAL",
  "context_json": {
    "connection_string": "postgresql://...",
    "timeout_seconds": 10
  }
}
```

### API Errors
```json
{
  "error_type": "api_timeout",
  "severity": "ERROR",
  "context_json": {
    "api_name": "Claude",
    "elapsed_seconds": 30,
    "expected_timeout": 30
  }
}
```

### Extraction Errors
```json
{
  "error_type": "content_extraction_failed",
  "severity": "ERROR",
  "context_json": {
    "url": "https://portal.example.com/report/123",
    "html_length": 45000,
    "selector": ".report-content"
  }
}
```
