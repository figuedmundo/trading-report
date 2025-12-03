# Trading Report Monitor - Complete Users Manual

## Table of Contents

1. [Overview](#overview)
2. [Quick Start Guide](#quick-start-guide)
3. [System Configuration](#system-configuration)
4. [N8N Workflow Configuration](#n8n-workflow-configuration)
5. [Using the System](#using-the-system)
6. [API Reference](#api-reference)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)
9. [Security Best Practices](#security-best-practices)
10. [Maintenance](#maintenance)

---

## Overview

**Trading Report Monitor** is an automated system that:
- Receives trading reports via email webhooks
- Extracts content from password-protected web portals using browser automation
- Analyzes reports with AI
- Delivers summaries via email and Telegram

### Key Features

- **Automated Email Processing**: Receives and parses trading report emails
- **Secure Portal Access**: Browser automation with encrypted credentials
- **AI Analysis**: Summarizes and analyzes report content
- **Multi-Channel Notifications**: Email and Telegram delivery
- **Security-First Architecture**: IP whitelisting, rate limiting, signature validation
- **Audit Trail**: Complete logging of all operations
- **Homelab-Friendly**: Single Docker Compose deployment

### Architecture

The system consists of multiple microservices orchestrated by N8N:

```
Email Event
    ↓
Email Webhook Service (validates, parses)
    ↓
N8N Workflow (orchestrates)
    ├─→ Playwright Scraper (extracts from portal)
    ├─→ AI Analyzer (analyzes content)
    └─→ Notification Service (sends alerts)
         ├─→ Email Delivery
         ├─→ Telegram Messages
         └─→ Audit Logging
```

---

## Quick Start Guide

### Prerequisites

- Docker and Docker Compose installed
- Email service provider account (Gmail, Mailgun, SendGrid, etc.)
- Trading portal credentials (username/password)
- PostgreSQL 15+ running in Docker
- (Optional) Telegram bot token for notifications

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone <your-repo> trading-report
cd trading-report

# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### Step 2: Configure Environment Variables

**Essential variables** (see [System Configuration](#system-configuration) for full list):

```bash
# Email Provider
TRADING_PORTAL_USERNAME=your_username
TRADING_PORTAL_PASSWORD=your_password

# AI Provider (choose one)
ANTHROPIC_API_KEY=sk-ant-...
# OR
GROQ_API_KEY=...

# Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SMTP_HOST=smtp.gmail.com
SMTP_USER=your@email.com
SMTP_PASSWORD=your_app_password

# Database
POSTGRES_PASSWORD=secure_password

# Webhook Security
WEBHOOK_SECRET_KEY=generate_with_openssl_rand_hex_32
```

### Step 3: Start the System

```bash
# Start all services (production mode)
make prod

# Or with logs visible (development mode)
make dev

# Check service health
make health
```

### Step 4: Configure Email Provider Webhook

Point your email service provider's webhook to:
```
https://your-domain.com/webhook/email
```

With authentication header matching your `WEBHOOK_SECRET_KEY`.

### Step 5: Test the System

```bash
# Send test email
curl -X POST http://localhost:5678/webhook/test \
  -H "Content-Type: application/json" \
  -d '{
    "from":"test@example.com",
    "subject":"Trading Report",
    "body":"Report content here"
  }'

# Check N8N workflow status
open http://localhost:5678
```

---

## System Configuration

### Environment Variables Reference

#### Email & Portal Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `TRADING_PORTAL_USERNAME` | Yes | Username for portal login | `john@example.com` |
| `TRADING_PORTAL_PASSWORD` | Yes | Password for portal login | `SecurePass123!` |
| `TRADING_PORTAL_URL` | No | Portal base URL | `https://portal.example.com` |

#### AI Provider (Choose One)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | If using Claude | Claude API key | `sk-ant-...` |
| `GROQ_API_KEY` | If using Groq | Groq API key | `gsk_...` |
| `AI_MODEL` | No | Model name (default: claude-3-sonnet) | `gpt-4` |

#### Email Notifications

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SMTP_HOST` | Yes | SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | No | SMTP port (default: 587) | `587` |
| `SMTP_USER` | Yes | Email address | `alerts@example.com` |
| `SMTP_PASSWORD` | Yes | Email password or app token | `apptoken123` |
| `SMTP_FROM_EMAIL` | No | From address (default: SMTP_USER) | `trading-alerts@example.com` |
| `REPORT_RECIPIENTS` | Yes | Comma-separated email list | `user1@example.com,user2@example.com` |

#### Telegram Notifications

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | If using Telegram | Bot token from @BotFather | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `TELEGRAM_CHAT_ID` | If using Telegram | Your chat ID | `123456789` |
| `TELEGRAM_ENABLED` | No | Enable Telegram (default: true) | `true` |

#### Database

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/trading_reports` |
| `POSTGRES_PASSWORD` | Yes | Postgres root password | `SecureDBPass123!` |
| `POSTGRES_USER` | No | Postgres user (default: postgres) | `postgres` |
| `POSTGRES_DB` | No | Database name (default: trading_reports) | `trading_reports` |

#### Webhook Security

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `WEBHOOK_SECRET_KEY` | Yes | 32+ character secret for signature validation | Generate: `openssl rand -hex 32` |
| `MAILGUN_IP_RANGES` | If using Mailgun | Mailgun IP CIDR ranges | `149.72.0.0/16,161.38.0.0/16` |
| `SENDGRID_IP_RANGES` | If using SendGrid | SendGrid IP CIDR ranges | `168.245.0.0/16,167.89.0.0/16` |
| `CUSTOM_ALLOWED_IPS` | No | Additional allowed IP ranges | `203.0.113.0/24` |

#### Rate Limiting

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RATE_LIMIT_PER_IP_MINUTE` | No | 5 | Requests per IP per minute |
| `RATE_LIMIT_PER_IP_HOUR` | No | 50 | Requests per IP per hour |
| `RATE_LIMIT_GLOBAL_HOUR` | No | 100 | Total requests per hour |
| `RATE_LIMIT_BAN_THRESHOLD` | No | 10 | Failed attempts before ban |
| `RATE_LIMIT_BAN_DURATION_HOURS` | No | 1 | Ban duration in hours |

#### Security Alerts

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECURITY_ALERT_THRESHOLD` | No | 50 | Failed requests threshold |
| `SECURITY_ALERT_TELEGRAM` | No | true | Enable Telegram alerts |
| `SECURITY_ALERT_DEBOUNCE_MINUTES` | No | 10 | Alert debounce window |

#### Service Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ENVIRONMENT` | No | development | Environment (development, production) |
| `PORT` | No | 8000 | Service port |

---

## N8N Workflow Configuration

### Accessing N8N Dashboard

Once all services are running, access N8N at:
```
http://localhost:5678
```

The N8N interface allows you to:
- View and monitor workflows
- Check execution history
- Manually trigger workflows
- Edit workflow configurations

### Pre-Built Workflow: Email Report Processing

The system includes a main workflow that handles the complete email-to-notification pipeline.

#### Workflow Steps

1. **Email Webhook Trigger**
   - Receives email event from webhook service
   - Passes email metadata (from, subject, body, URL)

2. **Extract Report URL** (Data transformer)
   - Searches email body for report portal URL
   - Extracts URL for scraping

3. **Playwright Scraper** (HTTP Request Node)
   - Calls scraper service to extract report content
   - Inputs: Portal URL, username, password
   - Outputs: HTML content, extracted text, images, screenshots

4. **AI Analysis** (HTTP Request Node)
   - Sends extracted content to AI analyzer
   - Generates executive summary (200-300 words)
   - Extracts key trading signals
   - Returns sentiment analysis

5. **Notification Sender** (Conditional Logic)
   - Checks if analysis succeeded
   - Branches: Email + Telegram (both) or Email only
   - Formats messages based on channel

6. **Send Email Notification** (HTTP Request Node)
   - Formats HTML email with summary
   - Includes original report link
   - Sends via notification service

7. **Send Telegram Notification** (HTTP Request Node)
   - Formats message with emojis
   - Includes quick links
   - Sends to configured chat ID

8. **Audit Logging** (Data transformer)
   - Records workflow execution
   - Stores status, timestamps, errors
   - Saves to PostgreSQL via webhook

### Manual Workflow Import

If you need to re-import the workflow:

1. **Export workflow JSON**:
   ```bash
   # Workflows are stored in N8N database
   # No manual export needed - they persist
   ```

2. **Create New Workflow in N8N UI**:
   - Go to Workflows → Create New
   - Use the Web UI to configure nodes
   - Save with descriptive name

3. **Configure Webhook Trigger**:
   - Add "Webhook" trigger node
   - Set to POST method
   - URL path: `/webhook/email`
   - Authentication: Basic auth with email-webhook credentials

4. **Add Service Calls**:
   - Use "HTTP Request" nodes
   - Point to local service URLs:
     - Scraper: `http://playwright-scraper:8002/api/v1/scrape`
     - AI Analyzer: `http://ai-analyzer:8000/api/v1/analyze`
     - Notifications: `http://notification-service:8004/api/v1/notify`

### Customizing Workflows

#### Change Analysis Parameters

To modify what the AI analyzer extracts:

1. Open N8N UI → select workflow
2. Find "AI Analysis" HTTP Request node
3. Edit request body:
   ```json
   {
     "content": "{{ $node.DataTransformer.json.extracted_text }}",
     "focus": ["trading_signals", "risk_analysis"],
     "max_length": 300
   }
   ```

#### Change Notification Recipients

To send to different channels or recipients:

1. Find "Notification Sender" node
2. Modify recipient configuration:
   ```json
   {
     "email_recipients": ["user@example.com"],
     "telegram_enabled": true,
     "telegram_chat_ids": ["123456789"]
   }
   ```

#### Add New Steps to Workflow

Example: Add a database check before processing:

1. Add new "Function" node before webhook handler
2. Check if email was already processed:
   ```javascript
   // Prevent duplicate processing
   const emailId = $node.Webhook.json.message_id;
   return {
     isDuplicate: await checkDatabase(emailId)
   };
   ```

3. Use conditional logic to skip if duplicate

### Monitoring Workflow Execution

#### Via N8N Dashboard

1. Navigate to **Workflows**
2. Click workflow name
3. View **Execution History** tab showing:
   - Execution timestamp
   - Success/Failure status
   - Duration
   - Error messages (if failed)

#### Via Database Queries

```bash
make db-shell

# Check workflow execution logs
SELECT * FROM system_logs
WHERE service = 'n8n'
AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

# Count successful/failed executions
SELECT status, COUNT(*)
FROM execution_logs
GROUP BY status;
```

#### Via Logs

```bash
# Watch N8N logs in real-time
docker-compose logs -f n8n

# Search for specific workflow errors
docker-compose logs n8n | grep -i "error"
```

### Workflow Debugging

#### Common Issues

**Issue**: Workflow appears to run but no notifications sent
- Check "Send Email" or "Send Telegram" nodes for connection errors
- Verify SMTP/Telegram credentials in environment
- Check notification service health: `curl http://localhost:8004/health`

**Issue**: Scraper returns empty content
- Check if portal URL is correct
- Verify trading portal credentials haven't changed
- Check Playwright logs: `make logs-service SERVICE=playwright-scraper`
- Verify the portal login selectors haven't changed

**Issue**: AI analysis returns generic results
- Check if API key is still valid (Anthropic/Groq)
- Verify API rate limits haven't been exceeded
- Try submitting a test request directly to AI service:
  ```bash
  curl -X POST http://localhost:8000/api/v1/analyze \
    -H "Content-Type: application/json" \
    -d '{"content":"test trading report"}'
  ```

**Issue**: Webhook not triggering workflow
- Verify webhook service is running: `curl http://localhost:8001/health`
- Check webhook logs: `make logs-service SERVICE=email-webhook`
- Manually test webhook with `curl` (see Testing section)
- Verify N8N webhook URL matches email provider configuration

---

## Using the System

### How Email Processing Works

1. **Email Arrives**: Email service sends webhook to `/webhook/email`
2. **Validation**: Security checks (IP whitelist, rate limit, signature)
3. **Parsing**: Extract headers, body, and trading report indicators
4. **Orchestration**: N8N workflow triggered
5. **Parallel Processing**:
   - Playwright scraper extracts from portal
   - AI analyzer summarizes content
   - Notification service delivers results
6. **Audit**: All operations logged to PostgreSQL

### Manual Webhook Test

```bash
# Test with valid signature (replace with actual signature)
curl -X POST http://localhost:8001/webhook/email \
  -H "Content-Type: application/json" \
  -H "X-Signature: <calculated-hmac>" \
  -d '{
    "from": "broker@example.com",
    "subject": "Daily Trading Report",
    "body": "Your report is ready at https://portal.example.com/report/123"
  }'
```

### Checking Processing Status

**Via N8N Dashboard**:
```
http://localhost:5678
```
- View all workflows
- Monitor execution history
- Check for errors or failures
- Manually trigger workflows

**Via PostgreSQL**:
```bash
# Connect to database
make db-shell

# Check recent reports
SELECT id, email_from, status, created_at FROM reports LIMIT 10;

# Check analysis results
SELECT report_id, summary, created_at FROM analyses LIMIT 5;

# Check delivery logs
SELECT email_to, status, sent_at FROM notifications_delivery_log LIMIT 10;
```

### Viewing Logs

```bash
# All services
make logs

# Specific service
make logs-service SERVICE=email-webhook
make logs-service SERVICE=playwright-scraper
make logs-service SERVICE=ai-analyzer
make logs-service SERVICE=notification-service

# Follow logs in real-time
docker-compose logs -f email-webhook

# Search logs for errors
docker-compose logs | grep ERROR
```

### Triggering Manual Analysis

```bash
# Via N8N UI (http://localhost:5678):
# 1. Navigate to Workflows
# 2. Select "Email Report Processing"
# 3. Click "Execute"
# 4. Provide test data

# Via API:
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your trading report content...",
    "source": "manual_test"
  }'
```

---

## API Reference

### Email Webhook Service

#### Health Check
```http
GET /health
```

**Response**:
```json
{
  "status": "ok",
  "timestamp": "2025-11-28T10:30:00Z"
}
```

#### Receive Webhook
```http
POST /webhook/email
Content-Type: application/json
X-Signature: <HMAC-SHA256>

{
  "from": "sender@example.com",
  "subject": "Report Title",
  "body": "Email content with report details"
}
```

**Success Response** (200):
```json
{
  "status": "accepted",
  "message": "Webhook received and queued"
}
```

**Error Responses**:
- 401: Invalid signature
- 403: IP not whitelisted
- 429: Rate limit exceeded
- 400: Malformed request

#### Rate Limit Headers

All responses include:
```
X-RateLimit-Remaining: 4
X-RateLimit-Reset: 1732798200
Retry-After: 60
```

### AI Analyzer Service

#### Analyze Content
```http
POST /api/v1/analyze
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Trading report content to analyze",
  "report_id": "uuid-here"
}
```

**Response** (200):
```json
{
  "report_id": "uuid-here",
  "summary": "Key findings...",
  "key_points": ["Point 1", "Point 2"],
  "sentiment": "positive",
  "created_at": "2025-11-28T10:30:00Z"
}
```

### Notification Service

#### Send Email
```http
POST /api/v1/notify/email
Authorization: Bearer <token>
Content-Type: application/json

{
  "to": "user@example.com",
  "subject": "Trading Report Summary",
  "body": "HTML email content",
  "html": true
}
```

#### Send Telegram
```http
POST /api/v1/notify/telegram
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Trading report summary...",
  "chat_id": "123456789"
}
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Services Won't Start

**Symptom**: `docker-compose up` fails or services keep restarting

**Solutions**:
```bash
# Check if ports are already in use
lsof -i :8000  # Check port 8000
lsof -i :5432  # Check port 5432

# Clean up and rebuild
make clean
make dev-build
make dev

# Check Docker logs
docker-compose logs -f

# Verify .env file exists
ls -la .env

# Check .env has all required variables
grep WEBHOOK_SECRET_KEY .env
```

#### 2. Database Connection Errors

**Symptom**: `Error: could not connect to database`

**Solutions**:
```bash
# Verify database is running
docker-compose ps postgres

# Check database credentials in .env
grep DATABASE_URL .env
grep POSTGRES_PASSWORD .env

# Test connection manually
make db-shell

# Reset database (⚠️ deletes all data)
make db-reset
make db-migrate
```

#### 3. Webhook Not Receiving Emails

**Symptom**: No emails processed, webhook not triggered

**Solutions**:
```bash
# Verify webhook service is running
curl http://localhost:8001/health

# Check webhook logs
make logs-service SERVICE=email-webhook

# Verify webhook URL is correct
# In email provider settings, confirm:
# - URL: https://your-domain.com/webhook/email
# - Method: POST
# - Headers: Content-Type: application/json

# Test webhook manually
curl -X POST http://localhost:8001/webhook/email \
  -H "Content-Type: application/json" \
  -d '{"from":"test@example.com","subject":"Test","body":"Test"}'

# Check rate limiting isn't blocking requests
SELECT COUNT(*) FROM security_events
WHERE event_type = 'rate_limit_exceeded'
AND created_at > NOW() - INTERVAL '1 hour';
```

#### 4. Signature Validation Failures

**Symptom**: Error 401 "Invalid Signature" or 403 "IP Not Whitelisted"

**Solutions**:
```bash
# Verify WEBHOOK_SECRET_KEY matches provider
grep WEBHOOK_SECRET_KEY .env

# Check IP allowlist configuration
grep IP_RANGES .env
grep CUSTOM_ALLOWED_IPS .env

# View recent security events
SELECT * FROM security_events
WHERE ip_address = '1.2.3.4'
ORDER BY created_at DESC LIMIT 10;

# Check if IP is banned
SELECT * FROM ip_bans
WHERE ip_address = '1.2.3.4'
AND banned_until > NOW();

# Temporarily bypass validation for testing
echo "SIGNATURE_VALIDATION_ENABLED=false" >> .env
make restart
```

#### 5. No Notifications Sent

**Symptom**: Reports analyzed but no email/Telegram received

**Solutions**:

**For Email**:
```bash
# Check SMTP configuration
grep SMTP .env

# Verify email provider allows app connections
# Gmail: Enable "Less secure app access" OR use app password
# Mailgun/SendGrid: Verify API key is valid

# Check notification logs
docker-compose logs notification-service | grep -i email

# Test email manually
curl -X POST http://localhost:8004/api/v1/notify/email \
  -H "Content-Type: application/json" \
  -d '{
    "to": "your@email.com",
    "subject": "Test",
    "body": "Test message"
  }'
```

**For Telegram**:
```bash
# Verify bot token and chat ID
grep TELEGRAM .env

# Test bot token validity
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"

# Check if chat ID is correct (must be a number)
echo $TELEGRAM_CHAT_ID

# Send test message
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}&text=Test message"
```

#### 6. Portal Login Failures

**Symptom**: Scraper can't extract content from portal

**Solutions**:
```bash
# Verify portal credentials
grep TRADING_PORTAL .env

# Check portal URL is accessible
curl https://portal.example.com

# View scraper logs for login errors
make logs-service SERVICE=playwright-scraper

# Test login manually with browser automation
# (Usually requires SSH into container)
docker-compose exec playwright-scraper bash
python -c "from scraper import login_to_portal; login_to_portal()"

# Check if portal requires 2FA or other auth
# Review browser automation code
nano services/playwright-scraper/src/scraper.py
```

#### 7. AI Analysis Returns Generic Results

**Symptom**: Summaries are too brief or generic

**Solutions**:
```bash
# Check AI API key is valid
grep ANTHROPIC_API_KEY .env
# or
grep GROQ_API_KEY .env

# Verify correct model is configured
grep AI_MODEL .env

# Check API rate limiting/quota
# In your AI provider dashboard (api.anthropic.com or console.groq.com)

# View analysis logs for errors
make logs-service SERVICE=ai-analyzer

# Test API manually
curl -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "test"}]
  }'
```

#### 8. Database Disk Space Full

**Symptom**: "Error: no space left on device" or slow queries

**Solutions**:
```bash
# Check database size
docker exec trading-postgres du -sh /var/lib/postgresql/data

# Clean up old security events (older than 90 days)
make db-shell
DELETE FROM security_events WHERE created_at < NOW() - INTERVAL '90 days';

# Vacuum and analyze database
VACUUM ANALYZE;

# Check for bloated tables
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables WHERE schemaname NOT IN ('information_schema','pg_catalog')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### 9. Memory Usage Too High

**Symptom**: Containers using excessive memory, system slow

**Solutions**:
```bash
# Check container memory usage
docker stats

# Reduce Playwright instances (if applicable)
# Edit docker-compose.yml
# Reduce PLAYWRIGHT_POOL_SIZE or similar setting

# Reduce rate limit storage size
# In .env, reduce cache times
RATE_LIMIT_STORAGE_TTL=300  # seconds

# Restart services to clear memory
make restart
```

#### 10. Duplicate Reports Being Processed

**Symptom**: Same report processed multiple times

**Solutions**:
```bash
# Enable idempotency checking (if not already enabled)
grep IDEMPOTENCY_ENABLED .env

# Check for duplicate emails
SELECT email_id, COUNT(*)
FROM reports
GROUP BY email_id
HAVING COUNT(*) > 1;

# Clean up duplicates
DELETE FROM reports
WHERE id IN (
  SELECT id FROM reports r1
  WHERE EXISTS (
    SELECT 1 FROM reports r2
    WHERE r1.email_id = r2.email_id
    AND r1.id < r2.id
  )
);

# Enable deduplication if missing
echo "ENABLE_DEDUPLICATION=true" >> .env
```

---

## FAQ

### General Questions

**Q: How often are emails checked?**
A: Emails are processed in real-time when they arrive at your email provider's webhook endpoint. The system doesn't poll.

**Q: Can I process existing emails?**
A: Yes, manually forward emails to the system or trigger N8N workflows manually via the UI.

**Q: What happens if the system goes down?**
A: Email service providers queue webhooks and retry. When the system comes back online, queued emails are processed.

**Q: Can I change analysis parameters?**
A: Yes, edit the AI analysis prompt in the AI Analyzer service configuration or N8N workflow.

### Technical Questions

**Q: What database is used?**
A: PostgreSQL 15+. All data is stored locally (self-hosted).

**Q: Is data encrypted?**
A: Portal credentials are encrypted in the database. API keys are environment variables. HTTPS should be used in production.

**Q: How long are logs kept?**
A: Security events are kept for 90 days by default (configurable via `SECURITY_EVENT_RETENTION_DAYS`).

**Q: Can I backup the database?**
A: Yes, use `make db-backup`. Backups are stored in `./backups/`.

**Q: How do I restore a backup?**
A: Use `make db-restore` for interactive restore.

### Security Questions

**Q: What IP addresses should I whitelist?**
A: Whitelist your email provider's IP ranges:
- Mailgun: 149.72.0.0/16, 161.38.0.0/16 (check their docs)
- SendGrid: 168.245.0.0/16, 167.89.0.0/16 (check their docs)
- Gmail: Use the webhook authentication instead

**Q: How is the webhook secret key used?**
A: It's used to compute HMAC signatures that verify webhook authenticity. Generate with:
```bash
openssl rand -hex 32
```

**Q: What if rate limits block legitimate traffic?**
A: Adjust `RATE_LIMIT_PER_IP_MINUTE` and `RATE_LIMIT_PER_IP_HOUR` in `.env` to be more permissive.

**Q: How do I know if my system is secure?**
A: Check security events log:
```bash
make db-shell
SELECT event_type, COUNT(*) FROM security_events
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY event_type;
```

### Operational Questions

**Q: How do I update the system?**
A:
```bash
git pull origin main
make build
make restart
```

**Q: Can I run multiple instances?**
A: Yes, but coordinate database access. Database mutations should be serialized.

**Q: What's the recommended hardware?**
A: Minimum 2 CPU cores, 4GB RAM. For high volume, scale up resources.

**Q: Can I change the port?**
A: Yes, set `PORT` in `.env` and update port mappings in `docker-compose.yml`.

---

## Security Best Practices

### 1. Credential Management

✅ **DO**:
- Store credentials in `.env` file (outside Docker)
- Use strong passwords (16+ characters with mixed case, numbers, symbols)
- Rotate API keys regularly (monthly recommended)
- Keep `.env` out of version control (`gitignore` it)

❌ **DON'T**:
- Commit `.env` to git
- Share credentials via email/chat
- Use the same password for multiple services
- Store credentials in code or comments

### 2. Network Security

✅ **DO**:
- Use HTTPS in production
- Whitelist IP addresses for webhooks
- Use strong `WEBHOOK_SECRET_KEY` (32+ random characters)
- Enable rate limiting for DDoS protection
- Keep services on private network/VPN

❌ **DON'T**:
- Expose services directly to the internet without authentication
- Use HTTP for sensitive data
- Share webhook URLs publicly
- Disable signature validation in production

### 3. Database Security

✅ **DO**:
- Use strong `POSTGRES_PASSWORD`
- Keep PostgreSQL inside Docker (not exposed)
- Regular backups with `make db-backup`
- Monitor audit logs for suspicious activity
- Enable SSL for remote connections

❌ **DON'T**:
- Expose port 5432 to the internet
- Use default passwords
- Skip backups
- Run as root user in database

### 4. API Security

✅ **DO**:
- Rotate API keys (Anthropic, Groq, Telegram, etc.)
- Monitor API usage for unusual patterns
- Use environment variables for all secrets
- Implement request signing for webhooks
- Log all API calls for audit trail

❌ **DON'T**:
- Embed API keys in code
- Share API keys across environments
- Use development API keys in production
- Ignore API rate limits and quotas

### 5. Logging and Monitoring

✅ **DO**:
- Review security event logs regularly
- Set up alerts for suspicious patterns (50+ failures, IP bans, etc.)
- Keep logs for 90+ days for compliance
- Monitor rate limit violations
- Track failed authentication attempts

❌ **DON'T**:
- Log sensitive data (passwords, API keys)
- Ignore security warnings
- Delete audit logs without archiving
- Rely solely on logs (have monitoring too)

### 6. Access Control

✅ **DO**:
- Run N8N with authentication enabled
- Restrict access to database shell
- Use SSH keys (not passwords) for server access
- Implement firewall rules
- Audit who can access the system

❌ **DON'T**:
- Use weak N8N passwords
- Run without authentication
- Allow public access to admin interfaces
- Share server access widely

---

## Maintenance

### Daily Tasks

- Monitor logs for errors: `docker-compose logs --tail 100`
- Check system health: `make health`
- Review email processing status in N8N dashboard

### Weekly Tasks

- Review security events: `docker-compose exec postgres psql -U postgres -d trading_reports -c "SELECT COUNT(*) FROM security_events WHERE created_at > NOW() - INTERVAL '7 days' AND event_type = 'rate_limit_exceeded';"`
- Check database size: `docker exec trading-postgres du -sh /var/lib/postgresql/data`
- Verify backups are running: `ls -lah ./backups/`

### Monthly Tasks

- Rotate API keys (Anthropic, Groq, Telegram)
- Review and update rate limit settings based on traffic
- Clean up old security events (keep 90+ days)
- Test disaster recovery (restore from backup)
- Review system performance metrics

### Quarterly Tasks

- Update dependencies: `make update`
- Security audit of configuration
- Review and update access controls
- Capacity planning based on growth

### Backup and Recovery

**Create Backup**:
```bash
make db-backup
# Backup stored in ./backups/trading_reports_YYYY-MM-DD_HHMMSS.sql
```

**Restore from Backup**:
```bash
make db-restore
# Interactive prompt to select backup file
```

**Verify Backup**:
```bash
# Check backup file exists and is recent
ls -lh ./backups/

# Verify backup contains expected tables
file ./backups/trading_reports_*.sql
head -20 ./backups/trading_reports_*.sql
```

### Updating the System

```bash
# Pull latest code
git pull origin main

# Rebuild images with new code
make build

# Restart all services
make restart

# Verify services are healthy
make health

# Check logs for errors
make logs
```

### Clearing Cache and Resetting

```bash
# Clear IP allowlist cache (reloads from database)
# Just restart the service
docker-compose restart email-webhook

# Clear rate limit counters (resets all limits)
# Requires service restart
make restart

# Reset entire database (⚠️ DELETES ALL DATA)
make db-reset
make db-migrate
```

---

## Getting Help

### Documentation References

- **Product Overview**: `/agent-os/product/mission.md`
- **Technical Architecture**: `/agent-os/product/tech-stack.md`
- **Database Schema**: `/agent-os/specs/*/spec.md`
- **Code Standards**: `/agent-os/standards/`
- **Service READMEs**: `/services/*/README.md`

### Debugging Commands

```bash
# View all logs with timestamps
docker-compose logs --timestamps

# Search logs for errors
docker-compose logs | grep -i error

# Interactive database access
make db-shell

# Check running containers
docker-compose ps

# Check container resource usage
docker stats

# Interactive shell in container
make shell SERVICE=email-webhook

# View specific service configuration
docker-compose config | grep -A 20 "email-webhook:"
```

### Support Channels

- Review GitHub issues
- Check existing documentation
- Enable DEBUG logging: `LOG_LEVEL=DEBUG`
- Export logs for analysis: `docker-compose logs > system.log`

---

**Last Updated**: November 28, 2025
**Version**: 1.0.0
**Compatible With**: Trading Report Monitor v1.0+
