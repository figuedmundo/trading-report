# N8N Workflow Templates

This directory contains N8N workflow templates that you can import into your N8N instance. Each template is a complete, production-ready workflow for different trading report automation scenarios.

## Available Workflows

### 1. Email Report Processing (`01-email-report-processing.json`)

**Purpose**: Main workflow that processes email triggers, extracts report URLs, scrapes content, analyzes with AI, and sends notifications.

**Workflow Steps**:
1. Webhook trigger from email service
2. Extract report URL from email body
3. Scrape content from portal (Playwright)
4. Analyze content with AI
5. Check analysis success
6. Send email notification
7. Send Telegram notification
8. Log to audit trail

**Inputs**:
- Email from (sender address)
- Email subject
- Email body (must contain report URL)

**Outputs**:
- Email notification to original sender
- Telegram notification to configured chat
- Audit log entry in database

**Requirements**:
- Email webhook service running
- Playwright scraper service running
- AI analyzer service running
- Notification service running

**Configuration**:
Before importing, ensure these services are running and environment variables are set:
- `TELEGRAM_CHAT_ID` (for Telegram notifications)
- `AI_PROVIDER` (anthropic or groq)

### 2. Additional Workflows (Coming Soon)

- `02-manual-report-trigger.json` - Manual report submission via N8N UI
- `03-scheduled-health-check.json` - Periodic health checks of all services
- `04-error-recovery.json` - Automatic retry logic for failed processing
- `05-analytics-dashboard.json` - Generate daily/weekly summary reports

## Importing a Workflow

### Method 1: Import from File (Recommended)

1. Open N8N dashboard: http://localhost:5678
2. Click **Import Workflow** in the top menu
3. Select **From File**
4. Choose the JSON file from `/docs/n8n-workflows/`
5. Review the workflow (don't execute yet)
6. Click **Save & Activate**

### Method 2: Copy-Paste JSON

1. Open the `.json` file in a text editor
2. Copy the entire JSON content
3. In N8N, click **Import Workflow**
4. Select **From URL or Raw JSON**
5. Paste the JSON content
6. Click **Save & Activate**

### Method 3: Use N8N CLI

```bash
# If N8N is running in Docker
docker-compose exec n8n n8n import workflow --input ./workflows/01-email-report-processing.json
```

## Configuring Imported Workflows

After importing, you may need to configure:

### API Endpoints

Workflows reference service endpoints. Ensure they match your deployment:

```javascript
// In webhook and HTTP request nodes, verify URLs:
http://service-name:port/api/v1/endpoint

// For local development:
http://localhost:8002/api/v1/scrape
http://localhost:8000/api/v1/analyze
http://localhost:8004/api/v1/notify

// For Docker Compose (same network):
http://playwright-scraper:8002/api/v1/scrape
http://ai-analyzer:8000/api/v1/analyze
http://notification-service:8004/api/v1/notify
```

### Environment Variables

Workflows can reference environment variables:

```javascript
// Example: Access environment variable in expression
{{ process.env.TELEGRAM_CHAT_ID }}

// This requires the variable to be passed to N8N container:
TELEGRAM_CHAT_ID=123456789
WEBHOOK_SECRET_KEY=your_secret_key
AI_PROVIDER=anthropic
```

### Dynamic AI Configuration (Advanced)

You can dynamically switch AI providers or models within the workflow (e.g., based on email subject keywords).

In the **Analyze Report** (HTTP Request) node, add headers:
- `X-AI-Provider`: `{{ $json.emailSubject.includes('Use Groq') ? 'groq' : 'anthropic' }}`
- `X-LLM-Model`: `gemini-2.0-flash`

### Webhook Paths

Each workflow's webhook trigger has a path. When importing, note:

```
Webhook Path: /webhook/trading-reports
Full URL: http://localhost:5678/webhook/trading-reports
```

When sending emails to the webhook:
```bash
curl -X POST http://localhost:8001/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: <signature>" \
  -d '{
    "from": "sender@example.com",
    "subject": "Trading Report Available",
    "body": "New report available at https://portal.example.com/report/123"
  }'
```

## Testing Workflows

### Test Mode (Safe)

1. Open workflow in N8N editor
2. Click **Test Workflow** or **Execute Workflow**
3. Workflow runs with test data (doesn't send actual notifications)
4. Review results in execution history

### Execute with Real Data

1. Open workflow editor
2. Click **Execute Workflow** (top right)
3. Provide actual input data
4. Workflow executes and sends real notifications

### View Execution History

1. Open workflow
2. Click **Executions** (bottom left)
3. View logs for each workflow run
4. Click execution to see details and error messages

## Customization Examples

### Change Recipients

In "Send Email Notification" node, modify the recipients:

```javascript
// Change from:
"recipients": {
  "email": ["{{$node[\"Extract Report URL\"]..json.emailFrom}}"]
}

// To:
"recipients": {
  "email": ["admin@yourdomain.com", "analyst@yourdomain.com"]
}
```

### Change Notification Channels

To skip Telegram notifications:

1. Open workflow
2. Right-click "Send Telegram Notification" node
3. Click **Delete** or **Deactivate**

To add SMS notifications:

1. Find "Send Telegram Notification" node
2. Duplicate it (right-click → Copy)
3. Change node type to "SMS Service" (or your provider)
4. Update recipients field

### Add Conditional Logic

In "Analysis Success Check" node, add more conditions:

```javascript
// Current: Only true branch sends notifications
// Enhanced: Add validation before sending

conditions: [
  // Condition 1: Analysis succeeded
  {
    value1: "{{$node['AI Analysis'].json.status}}",
    condition: "equal",
    value2: "success"
  },
  // Condition 2: Confidence score high enough
  {
    value1: "{{$node['AI Analysis'].json.confidence}}",
    condition: "greater",
    value2: 0.8
  }
]
```

### Schedule Periodic Execution

To run a workflow on a schedule (instead of webhook trigger):

1. Delete the "Email Webhook Trigger" node
2. Add new "Cron" node from core nodes
3. Configure schedule (e.g., "Every day at 9 AM")
4. Connect to "Extract Report URL" (or next step)

Example Cron schedules:
```
0 0 * * * - Every day at midnight (UTC)
0 9 * * 1-5 - Every weekday at 9 AM
0 */6 * * * - Every 6 hours
*/15 * * * * - Every 15 minutes
```

## Monitoring & Alerts

### View Workflow Metrics

In N8N Dashboard:
1. Click **Workflows**
2. Select workflow name
3. View execution stats (count, success rate, average duration)

### Set Up Alerts for Failures

In workflow editor:

1. After final node, add new node "Notification"
2. In expression, add condition:
   ```javascript
   {{ $node['Audit Log Entry'].json.workflowStatus === 'error' }}
   ```
3. Configure to send email/Telegram alert

### Monitor via Health Service

The health monitoring service tracks N8N workflow executions:

```bash
# Get N8N health status
curl http://localhost:8003/api/v1/health/status

# Get workflow execution errors
curl 'http://localhost:8003/api/v1/health/errors?severity=CRITICAL&hours=24'
```

## Troubleshooting Workflows

### Workflow Won't Execute

1. Check N8N logs: `docker-compose logs n8n`
2. Verify webhook path is correct
3. Ensure all service endpoints are reachable: `curl http://service:port/health`

### Notifications Not Sending

1. Check "Send Email Notification" and "Send Telegram Notification" nodes
2. Verify service URLs point to correct endpoints
3. Check notification service logs: `docker-compose logs notification-service`
4. Verify SMTP/Telegram credentials in environment

### Data Not Flowing Between Nodes

1. Check node connections (right-click → Show Connection)
2. Verify output field names match input field names in next node
3. Use expressions to access data: `{{ $node['previous-node'].json.fieldName }}`

### Timeout Errors

Increase timeout in HTTP request nodes:
```javascript
// In HTTP Request node options:
{
  "timeout": 120  // Increase from 60 to 120 seconds
}
```

## Best Practices

1. **Version Control**: Export workflows and commit JSON files to git
2. **Test Before Deploy**: Always test in a staging workflow first
3. **Use Variables**: Store credentials in N8N environment variables, not hardcoded
4. **Monitor Execution**: Check execution history for errors
5. **Document Changes**: Add notes to workflow describing recent modifications
6. **Backup Workflows**: Regularly export workflow JSON for backup

## Support

For help:
- See `/USERS_MANUAL.md` N8N section
- Check N8N logs: `docker-compose logs n8n`
- Review execution history in N8N dashboard
- Check service-specific logs for errors