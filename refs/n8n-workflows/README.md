# N8N Workflows for Health Monitoring

This directory contains reference N8N workflow configurations for health monitoring and error alerting.

## Workflows

### 1. Health Status Monitor (Scheduled)

**Purpose**: Monitor health status of all 5 services and alert if degraded.

**Trigger**: Scheduler node (every 5 minutes)

**Steps**:
1. Scheduler: Run every 300 seconds
2. HTTP Request: GET `/api/v1/health/status` from health-monitoring service
3. Filter: Check if `overall_status != "healthy"`
4. Conditional: If degraded, send alert email
5. Database: Log workflow execution

**Environment Variables**:
```
HEALTH_MONITORING_URL=http://health-monitoring:8003
```

**Workflow Logic**:
```
IF overall_status = "healthy" THEN
  Log: All services healthy
ELSE IF overall_status = "degraded" THEN
  Send Alert Email:
    Subject: Health Monitoring Alert - Service Degraded
    Body: List services with status != "up"
ELSE (unhealthy)
  Send Urgent Alert Email:
    Subject: CRITICAL - Service Down!
    Body: List all down services
END
```

**Expected Output**:
```json
{
  "status": "success",
  "overall_status": "healthy",
  "services_checked": 5,
  "alerts_sent": 0
}
```

---

### 2. Error Alert Workflow (Scheduled)

**Purpose**: Detect and alert on new CRITICAL errors within last hour.

**Trigger**: Scheduler node (every 1 minute)

**Steps**:
1. Scheduler: Run every 60 seconds
2. HTTP Request: GET `/api/v1/health/errors?severity=CRITICAL&hours=1`
3. Function: Filter errors newer than last check (store last_check_time in workflow memory)
4. Filter: Check if new errors found
5. Conditional: If errors found, compose email
6. Email: Send alert with error details formatted in table
7. Database: Log workflow execution

**Workflow Logic**:
```
last_check_time = workflow.memory.get("last_check_time") OR (now - 1 hour)

Call: GET /api/v1/health/errors?severity=CRITICAL&hours=1
new_errors = filter(errors where error_timestamp > last_check_time)

IF new_errors.length > 0 THEN
  email_body = format_error_table(new_errors)
  Send Email:
    To: ALERT_EMAIL_ADMIN
    Subject: CRITICAL Errors Detected
    Body: email_body

  workflow.memory.last_check_time = now
END
```

**Error Table Format**:
```
| Service Name | Error Type | Message | Time |
|---|---|---|---|
| ai-analyzer | api_timeout | Claude API request timeout after 30s | 14:15 |
| playwright-scraper | login_failed | Failed to login to portal | 14:10 |
```

---

### 3. Health Check Aggregation Workflow (Manual)

**Purpose**: Manually trigger and review comprehensive health check for all services.

**Trigger**: Manual (webhook or button click)

**Steps**:
1. HTTP Request: POST `/api/v1/health/check/email-webhook`
2. HTTP Request: POST `/api/v1/health/check/playwright-scraper`
3. HTTP Request: POST `/api/v1/health/check/ai-analyzer`
4. HTTP Request: POST `/api/v1/health/check/notification-service`
5. HTTP Request: POST `/api/v1/health/check/n8n`
6. Merge: Combine all results
7. Filter: Check for any "down" or "degraded" status
8. Conditional: Send summary email if needed
9. Database: Log execution

**Response Merge Format**:
```json
{
  "timestamp": "2024-12-03T14:30:45Z",
  "checks_executed": 5,
  "results": [
    {"service": "email-webhook", "status": "up", "duration_ms": 120},
    {"service": "playwright-scraper", "status": "up", "duration_ms": 145},
    ...
  ],
  "overall_status": "healthy"
}
```

---

### 4. Daily Error Report Workflow

**Purpose**: Generate daily summary of errors for review.

**Trigger**: Scheduler node (daily at 9:00 AM)

**Steps**:
1. Scheduler: Daily trigger at 09:00 UTC
2. HTTP Request: GET `/api/v1/health/errors?hours=24&limit=100`
3. Function: Group errors by service and severity
4. Template: Format HTML report with statistics
5. Email: Send daily report to ALERT_EMAIL_ADMIN
6. Database: Log report generation

**Daily Report Format**:
```
Subject: Daily Error Report - December 3, 2024

Summary:
- Total Errors: 42
- Critical: 5 (12%)
- Error: 20 (48%)
- Warning: 17 (40%)

By Service:
- email-webhook: 8 errors (6 ERROR, 2 WARNING)
- playwright-scraper: 12 errors (2 CRITICAL, 10 ERROR)
- ai-analyzer: 15 errors (3 CRITICAL, 12 ERROR)
- notification-service: 5 errors (5 ERROR)
- n8n: 2 errors (2 WARNING)

Top Issues:
1. login_failed (playwright-scraper): 6 occurrences
2. api_timeout (ai-analyzer): 5 occurrences
3. email_send_failed (notification-service): 5 occurrences
```

---

### 5. Alert State Reset Workflow (Scheduled)

**Purpose**: Monitor and reset alert states for resolved errors.

**Trigger**: Scheduler node (every 10 minutes)

**Steps**:
1. Scheduler: Run every 600 seconds
2. Database: Query alert_state table for old alerts
3. Database: For each alert with no new errors in last 5 minutes, reset state
4. HTTP Request: POST to health-monitoring to update alert state
5. Log: Record state resets

**Alert State Reset Logic**:
```
FOR each row in alert_state:
  last_error_time = (SELECT MAX(error_timestamp) FROM error_logs
                     WHERE service_name = alert_state.service_name
                     AND error_type = alert_state.error_type)

  IF (now - last_error_time) > ALERT_AUTO_RESOLVE_WINDOW THEN
    UPDATE alert_state:
      consecutive_failure_count = 0
      alert_suppressed_until = NULL
    Log: "Alert resolved: {service_name}.{error_type}"
  END
END
```

---

## Setup Instructions

### 1. Create Environment Variables in N8N

1. Go to N8N UI: http://localhost:5678
2. Settings → Environment Variables
3. Add these variables:

```
HEALTH_MONITORING_URL=http://health-monitoring:8003
ALERT_EMAIL_ADMIN=admin@example.com
NOTIFICATION_SERVICE_URL=http://notification-service:8001
POSTGRES_HOST=postgres
POSTGRES_DB=trading_reports
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=<your_password>
```

### 2. Configure PostgreSQL Connection in N8N

1. In N8N UI: Credentials → PostgreSQL
2. Create new credential with:
   - Host: `{{ $env.POSTGRES_HOST }}`
   - Database: `{{ $env.POSTGRES_DB }}`
   - User: `{{ $env.POSTGRES_USER }}`
   - Password: `{{ $env.POSTGRES_PASSWORD }}`
   - Port: 5432

### 3. Create Workflows

For each workflow listed above:

1. Create new workflow in N8N
2. Name it (e.g., "Health Status Monitor")
3. Add nodes as described in workflow steps
4. Configure each node with proper credentials and parameters
5. Test the workflow
6. Activate the workflow (enable schedule if applicable)

### 4. Email Configuration

For email nodes in workflows, ensure N8N has email provider configured:

**Gmail (SMTP)**:
1. Enable 2FA on Gmail account
2. Generate app password
3. In N8N Credentials → Gmail SMTP:
   - Host: smtp.gmail.com
   - Port: 587
   - Email: your-email@gmail.com
   - Password: <app-password>

**Alternative Providers**:
- SendGrid
- Mailgun
- AWS SES
- Custom SMTP server

## Node Reference

### HTTP Request Node Configuration

**Health Status Check**:
```
Method: GET
URL: {{ $env.HEALTH_MONITORING_URL }}/api/v1/health/status
Headers: { "Content-Type": "application/json" }
Response: JSON
```

**Error Retrieval**:
```
Method: GET
URL: {{ $env.HEALTH_MONITORING_URL }}/api/v1/health/errors?severity=CRITICAL&hours=1
Headers: { "Content-Type": "application/json" }
Response: JSON
```

**Manual Health Check**:
```
Method: POST
URL: {{ $env.HEALTH_MONITORING_URL }}/api/v1/health/check/{{ serviceName }}
Headers: { "Content-Type": "application/json" }
Body: {}
Response: JSON
```

### PostgreSQL Node Configuration

**Query Recent Alerts**:
```sql
SELECT * FROM alert_logs
WHERE alert_timestamp > NOW() - INTERVAL '1 hour'
ORDER BY alert_timestamp DESC
LIMIT 100;
```

**Log Workflow Execution**:
```sql
INSERT INTO error_logs
  (error_timestamp, service_name, error_type, severity, message, context_json)
VALUES
  (NOW(), 'n8n', 'workflow_execution', 'INFO',
   'Workflow {{ $workflowName }} executed',
   '{"workflow_id": "{{ $workflowId }}", "status": "{{ $executionStatus }}"}');
```

### Filter Node Examples

**Check Health Status**:
```javascript
$json.overall_status !== "healthy"
```

**Check for Errors**:
```javascript
$json.errors && $json.errors.length > 0
```

**Check Service Status**:
```javascript
$json.services.some(s => s.status !== "up")
```

## Monitoring & Troubleshooting

### Check Workflow Execution History

1. In N8N: Click on workflow
2. View "Executions" tab
3. See last execution status and logs

### Common Issues

**HTTP 503 (Service Unavailable)**:
- Check if health-monitoring service is running
- Verify port 8003 is accessible from N8N container
- Check N8N service logs: `docker-compose logs n8n`

**Email Not Sending**:
- Verify SMTP credentials in N8N
- Check email address is valid
- Review notification service logs

**Database Errors**:
- Verify PostgreSQL is running
- Check database credentials
- Review database connection logs

**Timeout Errors**:
- Health-monitoring service taking too long to respond
- Increase HTTP request timeout in node configuration
- Check for slow database queries in health-monitoring

### Debug Tips

1. **Add logging nodes**: Insert "Log" nodes between HTTP requests to see data flow
2. **Test individual nodes**: Right-click node → "Execute this node only"
3. **View node output**: Click "Preview" on data nodes to see JSON structure
4. **Check N8N logs**: `docker-compose logs -f n8n`
5. **Inspect health-monitoring logs**: `make logs-service SERVICE=health-monitoring`

## Examples

### Example: Alert on Service Down

```
IF input.overall_status = "unhealthy" THEN
  down_services = filter(services where status = "down")
  email_subject = "CRITICAL: " + down_services.length + " services down"
  email_body = "The following services are down:\n" +
               join(down_services.map(s => "- " + s.service_name + " (down for " +
                    compute_downtime(s) + ")"))
  Send Email(subject, body, to=ALERT_EMAIL_ADMIN)
END
```

### Example: Batch Errors into Report

```
errors = HTTP GET /api/v1/health/errors?severity=CRITICAL&hours=24
grouped = {}
FOR each error in errors:
  key = error.service_name + ":" + error.error_type
  IF grouped[key] not exists:
    grouped[key] = { count: 0, examples: [] }
  grouped[key].count += 1
  IF grouped[key].examples.length < 3:
    grouped[key].examples.push(error)

html_table = "<table><tr><th>Service</th><th>Type</th><th>Count</th></tr>"
FOR each group in grouped.values():
  html_table += "<tr><td>...</td><td>...</td><td>...</td></tr>"
html_table += "</table>"

Send Email(subject="Error Report", body=html_table)
```

## Best Practices

1. **Test workflows regularly**: Use "Execute workflow" button to test
2. **Monitor execution logs**: Check Executions tab for failures
3. **Set reasonable timeouts**: HTTP nodes should timeout after 10-30 seconds
4. **Use conditional logic**: Don't send alerts for every minor issue
5. **Archive old logs**: Periodically delete old execution logs to save storage
6. **Document workflows**: Add descriptions and comments in workflows
7. **Version control**: Export workflows and keep in version control
8. **Gradual rollout**: Test workflows in staging before activating

## Related Documentation

- Health Monitoring API: `/HEALTH_MONITORING.md`
- Health Monitoring Service: `/services/health-monitoring/`
- N8N Documentation: https://docs.n8n.io/
- N8N Nodes: https://docs.n8n.io/integrations/
