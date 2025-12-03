# Health Monitoring Quick Start Guide

## Overview

The health-monitoring service provides system-wide visibility into the health and errors of all 5 microservices. It runs continuously, checking service health every 60 seconds, generating alerts for critical errors, and maintaining a complete audit trail.

## Quick API Examples

### Check All Services Health

```bash
curl http://localhost:8003/api/v1/health/status
```

Response:
```json
{
  "timestamp": "2025-12-03T10:00:00Z",
  "overall_status": "healthy",
  "services": [
    {
      "service_name": "email-webhook",
      "status": "up",
      "check_timestamp": "2025-12-03T10:00:00Z",
      "check_duration_ms": 45
    },
    ...
  ]
}
```

### Get Recent CRITICAL Errors

```bash
curl "http://localhost:8003/api/v1/health/errors?severity=CRITICAL&hours=24&limit=10"
```

Response:
```json
{
  "timestamp": "2025-12-03T10:00:00Z",
  "count": 2,
  "errors": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "error_timestamp": "2025-12-03T09:30:00Z",
      "service_name": "email-webhook",
      "error_type": "login_failure",
      "severity": "CRITICAL",
      "message": "Failed to authenticate with trading portal",
      "correlation_id": "req-abc123",
      "source_report_id": "report-123"
    }
  ]
}
```

### Trigger Manual Health Check

```bash
curl -X POST http://localhost:8003/api/v1/health/check/ai-analyzer
```

### Filter Errors by Service and Severity

```bash
# Get all ERROR level issues from email-webhook in last 48 hours
curl "http://localhost:8003/api/v1/health/errors?service=email-webhook&severity=ERROR&hours=48&limit=50"
```

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Health Check Configuration
HEALTH_CHECK_INTERVAL=60              # Check every 60 seconds
HEALTH_CHECK_TIMEOUT=5               # 5 second timeout per service
ENABLE_HEALTH_MONITORING=true        # Enable health monitoring

# Alert Configuration
ALERT_EMAIL_ADMIN=ops@example.com    # Where to send critical alerts
ALERT_BATCH_WINDOW=60                # Batch errors within 60 minutes
ALERT_AUTO_RESOLVE_WINDOW=5          # Suppress re-alerts for 5 minutes

# Data Retention
ERROR_LOG_RETENTION_DAYS=30          # Keep errors for 30 days
HEALTH_CHECK_RETENTION_DAYS=7        # Keep health checks for 7 days
```

## How It Works

### Health Checks

The system checks all 5 services every 60 seconds:

1. **email-webhook** (port 8001): GET /health
2. **playwright-scraper** (port 8002): GET /health
3. **ai-analyzer** (port 8000): GET /health
4. **notification-service** (port 8004): GET /health
5. **n8n** (port 5678): HTTP GET /

Each service gets a status:
- **up**: Service is healthy and responding quickly
- **degraded**: Service responding but may have issues
- **down**: Service not responding or timeout

### Error Logging

When a service encounters an error, it's logged with:
- Service name
- Error type (login_failure, api_timeout, extraction_failure, etc.)
- Severity level (CRITICAL, ERROR, WARNING)
- Full error message and stack trace
- Context metadata (retry count, HTTP status, etc.)
- Correlation ID for tracing across services
- Affected report ID (if applicable)

### Alert Generation

Alerts are only sent for **CRITICAL** errors and follow these rules:

1. **First Error**: Alert sent immediately
2. **Duplicate Prevention**: No alert within 5 minutes of last alert for same error
3. **Batching**: Multiple errors of same type within 60 minutes = 1 alert
4. **Auto-Recovery**: If error resolves (no new errors for 5 minutes), counter resets
5. **Delivery**: Via email to ALERT_EMAIL_ADMIN

Example alert:
```
Subject: CRITICAL ERROR: email-webhook - login_failure

Service: email-webhook
Error Type: login_failure
Severity: CRITICAL
Time: 2025-12-03 10:30:00 UTC
Message: Failed to authenticate with trading portal
Consecutive Failures: 5

Recent Errors:
1. Failed to authenticate with trading portal (10:30:00)
2. Failed to authenticate with trading portal (10:25:00)
3. Failed to authenticate with trading portal (10:20:00)
...
```

## Monitoring Patterns

### Check Service Health Periodically

```bash
# Watch service health every 10 seconds
watch -n 10 'curl -s http://localhost:8003/api/v1/health/status | jq .overall_status'
```

### Monitor for New Critical Errors

```bash
# Check for CRITICAL errors from last hour
curl "http://localhost:8003/api/v1/health/errors?severity=CRITICAL&hours=1"
```

### Get Error Trend for Specific Service

```bash
# All errors from ai-analyzer in last 24 hours
curl "http://localhost:8003/api/v1/health/errors?service=ai-analyzer&hours=24&limit=100" | jq '.errors[] | {time: .error_timestamp, type: .error_type, severity: .severity}'
```

### Find Related Errors by Correlation ID

```bash
# After finding an error with correlation_id, trace all related errors
CORR_ID="req-abc123"
curl "http://localhost:8003/api/v1/health/errors?correlation_id=$CORR_ID"
```

## Interpreting Health Status

| Status | Meaning | Action |
|--------|---------|--------|
| healthy | All 5 services up | Normal operation |
| degraded | 1-4 services up | Monitor affected service |
| unhealthy | All services down | Check database, network, Docker |

## Common Issues & Solutions

### No Health Checks Running

**Symptom**: GET /health returns current data but health checks never update

**Solution**:
1. Check logs: `docker logs trading-health-monitoring`
2. Verify database connectivity: Check DATABASE_URL in environment
3. Check if health check task crashed: Restart with `docker-compose restart health-monitoring`

### Alerts Not Sending

**Symptom**: Errors logged but no alert emails received

**Solution**:
1. Verify ALERT_EMAIL_ADMIN is set
2. Check notification-service is running: `curl http://localhost:8004/health`
3. Check SMTP configuration in notification-service
4. Look for failed alerts: `curl "http://localhost:8003/api/v1/health/errors?severity=CRITICAL"`

### Too Many Duplicate Alerts

**Symptom**: Receiving multiple alerts for same error

**Solution**:
1. Increase ALERT_BATCH_WINDOW from 60 to 120 minutes
2. Increase ALERT_AUTO_RESOLVE_WINDOW from 5 to 10 minutes
3. Restart: `docker-compose restart health-monitoring`

### Database Growing Too Large

**Symptom**: Database disk usage increasing rapidly

**Solution**:
1. Check error_log_retention: `curl "http://localhost:8003/api/v1/health/errors?hours=720&limit=1000" | jq '.count'`
2. Reduce ERROR_LOG_RETENTION_DAYS from 30 to 14
3. Reduce HEALTH_CHECK_RETENTION_DAYS from 7 to 3
4. Cleanup runs automatically daily at midnight UTC

## Integration with N8N

### Display Health Status in N8N Dashboard

Create an HTTP Request node:
- Method: GET
- URL: `http://health-monitoring:8003/api/v1/health/status`
- Headers: Content-Type: application/json

The response contains overall_status you can use for conditional logic.

### Alert on Service Down

Create a Scheduler node (every 5 minutes):
1. HTTP Request: GET `/api/v1/health/status`
2. Filter: `overall_status != 'healthy'`
3. Email: Send alert if filter matches

### Log N8N Workflow Failures

Create an Error Workflow:
1. Capture error message and workflow name
2. HTTP Request: POST to health monitoring with error details
3. This gets logged as a workflow error for analysis

## Performance Notes

- Health endpoint queries: < 200ms
- Error retrieval with filtering: < 500ms
- Alert generation: < 1 second per 100 errors
- Database cleanup: < 1 minute daily
- Memory usage: ~100-150MB
- CPU usage: < 1% idle, peaks during checks

## Security Considerations

- Health endpoints are public (no auth needed)
- Error logs sanitized (no passwords or secrets)
- Alerts rate-limited (max 1 per hour per error type)
- All operations logged with timestamps
- Correlation IDs enable audit trails
- Database: SSL/TLS connections

## Next Steps

1. **Verify Setup**: `curl http://localhost:8003/health`
2. **Check All Services**: `curl http://localhost:8003/api/v1/health/status`
3. **Set Alert Email**: Update ALERT_EMAIL_ADMIN in .env
4. **Create N8N Workflows**: Use health endpoints for monitoring
5. **Configure Data Retention**: Adjust retention days for your needs

## Support & Troubleshooting

Full documentation: `/HEALTH_MONITORING_IMPLEMENTATION.md`

Debug logs: `docker logs -f trading-health-monitoring`

Database inspection:
```bash
# Connect to database
docker-compose exec postgres psql -U trading_user -d trading_reports

# Check recent errors
SELECT error_type, severity, COUNT(*) as count
FROM error_logs
WHERE error_timestamp > NOW() - INTERVAL '1 hour'
GROUP BY error_type, severity
ORDER BY count DESC;

# Check health check history
SELECT service_name, status, COUNT(*) as count
FROM health_checks
WHERE check_timestamp > NOW() - INTERVAL '1 hour'
GROUP BY service_name, status;
```

## Summary

The health-monitoring service provides:
- Real-time visibility into all 5 microservices
- Centralized error logging with context
- Smart alert generation (no spam)
- Complete audit trail
- REST API for custom integrations
- Background tasks for 24/7 monitoring

It's designed to run continuously with minimal overhead and help you quickly identify and resolve issues before they impact your trading report workflow.
