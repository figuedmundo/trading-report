# Trading Report System - Configuration Checklist

Use this checklist to verify your system is properly configured before running in production.

## Phase 1: Initial Setup

### Environment Files
- [ ] Copied `.env.example` to `.env`
- [ ] Added all required environment variables
- [ ] Verified no secrets are in `.env.example`
- [ ] Added `.env` to `.gitignore`
- [ ] Verified `.env` permissions are restricted (`chmod 600 .env`)

### Directory Structure
- [ ] Verified `docker-compose.yml` exists and is readable
- [ ] Verified all service directories exist under `services/`
- [ ] Verified database migration files exist in `database/`
- [ ] Created `docs/n8n-workflows/` and `docs/config-examples/` directories

## Phase 2: AI Provider Configuration

### Anthropic Claude Setup (if using)
- [ ] Created account at https://console.anthropic.com/
- [ ] Generated API key
- [ ] Set `ANTHROPIC_API_KEY` in `.env`
- [ ] Tested API key: `curl -H "Authorization: Bearer ${ANTHROPIC_API_KEY}" https://api.anthropic.com/`

### Groq Setup (if using)
- [ ] Created account at https://console.groq.com/
- [ ] Generated API key
- [ ] Set `GROQ_API_KEY` in `.env`
- [ ] Tested API key: `curl -H "Authorization: Bearer ${GROQ_API_KEY}" https://api.groq.com/`

### AI Provider Verification
- [ ] Only ONE AI provider configured (not both)
- [ ] API key is not empty
- [ ] API key format is correct for chosen provider
- [ ] Sufficient quota/credits available on AI provider account

## Phase 3: Database Configuration

### PostgreSQL Setup
- [ ] Generated secure password for `POSTGRES_PASSWORD` (minimum 16 characters)
- [ ] Generated secure password for `N8N_DB_PASSWORD`
- [ ] Generated secure password for `TRADING_USER_PASSWORD`
- [ ] All three passwords are different
- [ ] Set all three passwords in `.env`

### Database Initialization
- [ ] Run: `docker-compose up postgres`
- [ ] Wait for message: "database system is ready to accept connections"
- [ ] Verify no errors in logs: `docker-compose logs postgres | grep -i error`
- [ ] Stop database: `docker-compose down`

### Database Connectivity
- [ ] Verified `DATABASE_URL` format in `.env` (if using external DB)
- [ ] Tested database connection from local machine
- [ ] Verified database user has proper permissions

## Phase 4: Email/SMTP Configuration

### SMTP Credentials
- [ ] Provider: Gmail, Outlook, or custom SMTP
- [ ] Obtained SMTP host, port, username, password
- [ ] Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` in `.env`
- [ ] Set `SENDER_EMAIL` to a valid email address

### SMTP Verification
- [ ] Tested SMTP connection (see SETUP_GUIDE.md)
- [ ] Verified credentials work with test email
- [ ] For Gmail: Enabled 2-Step Verification and created App Password
- [ ] For Outlook: Verified password and account type (not Microsoft account)
- [ ] Email address is NOT already in use by another service

### Email Delivery
- [ ] Tested sending test email from SMTP account
- [ ] Verified emails reach recipient inbox (not spam)
- [ ] Set up SPF, DKIM records (optional but recommended for deliverability)

## Phase 5: Telegram Configuration (Optional)

### Telegram Bot Setup
- [ ] Created bot via @BotFather in Telegram
- [ ] Obtained bot token (format: `123456789:ABCDefGhIjKlmNoPqRsTuVwXyZ`)
- [ ] Set `TELEGRAM_BOT_TOKEN` in `.env`
- [ ] Started conversation with bot

### Telegram Chat ID
- [ ] Retrieved chat ID via getUpdates API
- [ ] Set `TELEGRAM_CHAT_ID` in `.env`
- [ ] Verified chat ID is numeric

### Telegram Verification
- [ ] Tested bot connectivity: `curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"`
- [ ] Verified response contains bot information (no errors)
- [ ] Sent test message via bot API

## Phase 6: Webhook Security

### Secret Key Generation
- [ ] Generated `WEBHOOK_SECRET_KEY` (minimum 32 characters, alphanumeric + special chars)
- [ ] Generated `N8N_ENCRYPTION_KEY` (minimum 32 characters)
- [ ] Both keys are unique (not duplicates)
- [ ] Set both in `.env`

### Webhook Configuration
- [ ] Set `SIGNATURE_VALIDATION_ENABLED=true` in `.env`
- [ ] Set `WEBHOOK_SECURITY_ENABLED=true` in `.env`
- [ ] All required IP whitelisting variables configured

### IP Whitelisting
- [ ] Identified email provider IP ranges (Mailgun, SendGrid, etc.)
- [ ] Set `MAILGUN_IP_RANGES` if using Mailgun
- [ ] Set `SENDGRID_IP_RANGES` if using SendGrid
- [ ] Set `CUSTOM_ALLOWED_IPS` for any additional trusted IPs
- [ ] Verified no conflicting IP ranges

## Phase 7: Network Configuration

### Local Development
- [ ] Set `N8N_HOST=localhost` for development
- [ ] Set `N8N_PROTOCOL=http` for development
- [ ] Set `WEBHOOK_URL=http://localhost:5678/webhook`

### Production/Public Domain
- [ ] Reserved domain name (e.g., `trading.yourdomain.com`)
- [ ] DNS A record points to your server IP
- [ ] Set `N8N_HOST=trading.yourdomain.com`
- [ ] Set `N8N_PROTOCOL=https`
- [ ] Set `WEBHOOK_URL=https://trading.yourdomain.com/webhook`
- [ ] Reverse proxy configured (Nginx, Traefik, etc.)
- [ ] SSL certificate configured (Let's Encrypt or self-signed)

## Phase 8: Trading Portal Credentials

### Portal Access
- [ ] Identified trading portal URL and login page
- [ ] Created or obtained trading account credentials
- [ ] Manually tested login in browser (to verify credentials work)
- [ ] Verified no CAPTCHA on login page (would block automated scraping)

### Credentials Storage
- [ ] Set `TRADING_PORTAL_USERNAME` in `.env`
- [ ] Set `TRADING_PORTAL_PASSWORD` in `.env`
- [ ] Verified credentials are NOT shared with other environments
- [ ] Checked password does NOT contain special characters that need escaping

## Phase 9: Service Port Configuration

### Port Availability
- [ ] Checked no other services using ports 5432, 5678, 8000-8004:
  ```bash
  lsof -i :5432  # PostgreSQL
  lsof -i :5678  # N8N
  lsof -i :8000  # AI Analyzer
  lsof -i :8001  # Email Webhook
  lsof -i :8002  # Playwright Scraper
  lsof -i :8003  # Health Monitoring
  lsof -i :8004  # Notification Service
  ```
- [ ] All checks returned empty (no conflicts)

### Port Mapping
- [ ] Firewall allows inbound traffic on required ports
- [ ] Port forwarding configured (if behind NAT/router)
- [ ] Verified ports are accessible from external network

## Phase 10: Health Check Configuration

### Health Monitoring Setup
- [ ] Set `ENABLE_HEALTH_MONITORING=true` in `.env`
- [ ] Set `HEALTH_CHECK_INTERVAL=60` (or desired interval)
- [ ] Set `HEALTH_CHECK_TIMEOUT=5`
- [ ] Set `ALERT_EMAIL_ADMIN` to valid email address
- [ ] Set `ALERT_BATCH_WINDOW=60`
- [ ] Set `ALERT_AUTO_RESOLVE_WINDOW=5`

### Alert Configuration
- [ ] Set `SECURITY_ALERT_THRESHOLD=50`
- [ ] Set `SECURITY_ALERT_TELEGRAM=true` (if using Telegram)
- [ ] Set `SECURITY_ALERT_DEBOUNCE_MINUTES=10`
- [ ] Verified alert email recipient exists and is accessible

### Data Retention
- [ ] Set `ERROR_LOG_RETENTION_DAYS=30`
- [ ] Set `HEALTH_CHECK_RETENTION_DAYS=7`
- [ ] Verified database has sufficient storage for retention period

## Phase 11: Docker Configuration

### Docker Images
- [ ] Docker installed: `docker --version`
- [ ] Docker Compose installed: `docker-compose --version`
- [ ] Built all images: `docker-compose build`
- [ ] All builds completed without errors

### Docker Network
- [ ] Network created: `docker network ls | grep trading-network`
- [ ] Volume structure correct: `docker volume ls | grep trading`

### Docker Logging
- [ ] Configured log rotation in docker-compose.yml
- [ ] Log driver set to "json-file" with size limits
- [ ] Max log size set to 10m per container

## Phase 12: N8N Workflow

### N8N Dashboard Access
- [ ] Started N8N: `docker-compose up n8n`
- [ ] Dashboard accessible at configured URL
- [ ] Created initial user account
- [ ] Set strong password for N8N admin user

### Workflow Setup
- [ ] Imported workflow from `/docs/n8n-workflows/01-email-report-processing.json`
- [ ] All nodes visible in workflow editor
- [ ] Webhook path is `/webhook/trading-reports`
- [ ] All service endpoints point to correct URLs
- [ ] Environment variables referenced correctly

### Webhook Configuration
- [ ] Created webhook trigger in workflow
- [ ] Method set to POST
- [ ] Path set to `/webhook/trading-reports`
- [ ] Webhook is active (blue dot indicator)

## Phase 13: System Integration Test

### Service Startup
- [ ] All services start without errors: `docker-compose up -d`
- [ ] All services healthy: `docker-compose ps`
- [ ] All health checks passing (wait 2-3 minutes)

### Service Connectivity
- [ ] Health endpoint responds: `curl http://localhost:8003/api/v1/health/status`
- [ ] Database is accessible to services
- [ ] All service URLs reachable from each other

### End-to-End Test
1. [ ] Access N8N dashboard without errors
2. [ ] Open workflow in N8N editor
3. [ ] Test webhook endpoint with curl:
   ```bash
   curl -X POST http://localhost:8001/webhook \
     -H "Content-Type: application/json" \
     -H "X-Webhook-Signature: $(echo -n 'test' | openssl dgst -sha256 -mac HMAC -macopt key:${WEBHOOK_SECRET_KEY} | cut -d' ' -f2)" \
     -d '{
       "from": "test@example.com",
       "subject": "Test Report",
       "body": "Check https://portal.example.com/report/123"
     }'
   ```
4. [ ] Workflow executes in N8N
5. [ ] Email notification received
6. [ ] Telegram notification received (if configured)
7. [ ] No errors in service logs

## Phase 14: Security Hardening

### Access Control
- [ ] N8N admin password is strong (12+ characters, mixed case, numbers, symbols)
- [ ] Database password is strong
- [ ] API keys are rotated (schedule: every 90 days)
- [ ] Service credentials not visible in logs

### Network Security
- [ ] Firewall restricts access to necessary ports only
- [ ] SSH/RDP access protected by strong passwords or keys
- [ ] HTTPS enabled for public endpoints
- [ ] Rate limiting configured on webhook endpoint

### Data Protection
- [ ] Sensitive fields encrypted in database
- [ ] Backups encrypted and stored securely
- [ ] Audit logs enabled and monitored
- [ ] PII is masked in logs

## Phase 15: Backup and Recovery

### Database Backup
- [ ] Created initial database backup
- [ ] Tested backup restoration
- [ ] Backup location is secure and redundant
- [ ] Backup schedule established (e.g., daily at midnight)

### Workflow Backup
- [ ] Exported N8N workflows as JSON
- [ ] Stored workflows in version control (git)
- [ ] Verified workflows can be re-imported from backup

### Disaster Recovery
- [ ] Documented recovery procedure
- [ ] Tested recovery from backup (dry run)
- [ ] Recovery time objective (RTO) defined
- [ ] Recovery point objective (RPO) defined

## Phase 16: Monitoring and Logging

### Centralized Logging
- [ ] All services logging to stdout/stderr
- [ ] Docker logs accessible: `docker-compose logs`
- [ ] Log aggregation solution in place (optional)

### Performance Monitoring
- [ ] Response time metrics collected
- [ ] Resource usage monitored (CPU, memory, disk)
- [ ] Database query performance tracked
- [ ] Alerts configured for anomalies

### Health Monitoring
- [ ] Health checks running on schedule
- [ ] Alerts being generated and delivered
- [ ] Error logs stored in database
- [ ] Health status dashboard accessible

## Phase 17: Documentation

### User Documentation
- [ ] USERS_MANUAL.md is comprehensive and up-to-date
- [ ] Configuration guide completed
- [ ] Troubleshooting guide reviewed
- [ ] Quick start guide available

### Operational Documentation
- [ ] System architecture documented
- [ ] Data flow diagram created
- [ ] Runbook for common tasks available
- [ ] Contact information for on-call support documented

## Phase 18: Final Verification

### Pre-Production Checklist
- [ ] All phases 1-17 completed
- [ ] All checkboxes marked as complete
- [ ] No outstanding issues or TODOs
- [ ] Security scan performed
- [ ] Performance baseline established

### Production Readiness
- [ ] Load testing completed
- [ ] Failover testing completed
- [ ] Backup restoration tested
- [ ] Team trained on operations
- [ ] Go/No-Go decision made

### Launch
- [ ] Configuration backed up and versioned
- [ ] Initial monitoring baseline established
- [ ] On-call support available
- [ ] Incident response plan in place
- [ ] System monitoring dashboard open

## Sign-Off

Configuration completed and verified by: ____________________ Date: __________

Reviewed by: ____________________ Date: __________

Approved for production by: ____________________ Date: __________

---

## Quick Troubleshooting Reference

If any checks fail, refer to:
- General issues: `/USERS_MANUAL.md` → Troubleshooting section
- Health monitoring: `/HEALTH_MONITORING.md` → Troubleshooting section
- Setup issues: `/docs/config-examples/SETUP_GUIDE.md` → Troubleshooting section
- N8N workflow: `/docs/n8n-workflows/README.md` → Troubleshooting Workflows section

For support, enable debug logging:
```bash
# In .env
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart
```

## Related Documents

- System Configuration: `docs/config-examples/.env.production`
- Setup Guide: `docs/config-examples/SETUP_GUIDE.md`
- Docker Overrides: `docs/config-examples/docker-compose.override.example.yml`
- N8N Workflows: `docs/n8n-workflows/README.md`
- User Manual: `USERS_MANUAL.md`
- Health Monitoring: `HEALTH_MONITORING.md`
