# 📊 Trading Report Automation System

Automated monitoring, scraping, analysis, and notification system for trading reports delivered via email.

## 🎯 Features

- **Automated Email Monitoring**: Webhook-based email monitoring with security validation (IP whitelisting, rate limiting, signature verification)
- **Browser Automation**: Playwright-based scraping with login handling and dynamic content extraction
- **AI Analysis**: Powered by Claude (Anthropic) or Groq for intelligent report summarization
- **Unified Multi-Channel Notifications**: Extensible notification service with email (SMTP) and Telegram (Bot API)
- **Reliable Delivery**: Exponential backoff retry, per-channel rate limiting, and complete audit trails
- **Persistent Storage**: PostgreSQL database with full audit trail and append-only delivery logs
- **Scalable Architecture**: Microservices design with Docker containers
- **Visual Workflow**: N8N for easy workflow management and modification
- **Health Monitoring & Alerting**: Continuous service monitoring with automatic CRITICAL error detection and batched email alerts
- **Monitoring**: Built-in health checks and optional Prometheus/Grafana stack

## 🏗️ Architecture

```
Email → Webhook Service → N8N → [Playwright Scraper] → PostgreSQL
   (Security checks)       ↓
   (IP validation)    [AI Analyzer] → Analysis Results → PostgreSQL
   (Rate limiting)         ↓
   (Signature valid)  [Unified Notification Service]
                           ↓
                      ┌────┴────┐
                 Email (SMTP)  Telegram (Bot API)
                 (retry+rate)  (retry+rate)
                      └────┬────┘
                    Delivery Audit Log

Health Monitoring (Continuous - every 60 seconds)
   └─> Checks all 5 services
       └─> Error detection & batched alerts
           └─> Sends alerts via Notification Service
```

### Services

1. **N8N** - Workflow orchestration and automation
2. **Email Webhook Service** - Email event processing with security validation
   - IP whitelisting and ban management
   - Rate limiting and signature validation
   - Email parsing and extraction
3. **Playwright Scraper** - Browser automation and web scraping
4. **AI Analyzer** - Report analysis using Claude/Groq
5. **Unified Notification Service** - Multi-channel delivery with retry logic and rate limiting
   - Email channel (SMTP with HTML templates)
   - Telegram channel (Bot API with message splitting)
   - Extensible for future channels (SMS, Slack, Discord)
6. **Health Monitoring Service** - Continuous service health checks and alerting
   - Background health check loop (every 60 seconds)
   - Error log collection and analysis
   - Alert generation with batching
   - Automatic email alerts on critical issues
7. **PostgreSQL** - Data persistence with audit trails
8. **Redis** - Caching and rate limiting (optional)
9. **Traefik** - Reverse proxy with SSL (optional)

## 📋 Prerequisites

- Docker 27.3+ and Docker Compose 2.29+
- 8GB RAM minimum (16GB recommended)
- 50GB disk space
- Domain name with DNS configured (for webhooks)
- API Keys:
  - Anthropic API key OR Groq API key
  - Telegram Bot Token
  - SMTP credentials

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo>
cd trading-report-automation
make setup
```

### 2. Configure Environment

Edit `.env` file with your credentials:

```bash
# Essential configuration
POSTGRES_PASSWORD=your_secure_password
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=your_chat_id

# Trading portal credentials
TRADING_PORTAL_USERNAME=your_username
TRADING_PORTAL_PASSWORD=your_password

# Email webhook
WEBHOOK_URL=https://trading-hook.yourdomain.com

# SMTP for sending emails
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your_app_password
```

### 3. Start Services

```bash
# Development mode (with logs)
make dev

# Production mode (detached)
make prod
```

### 4. Verify Installation

```bash
make health
```

Expected output:
```
✓ Playwright Scraper: UP
✓ AI Analyzer: UP
✓ Notification Service: UP
✓ N8N: UP
✓ PostgreSQL: UP
```

## 📖 Detailed Setup Guide

### Email Webhook Configuration

#### Option A: Using Mailgun (Recommended)

1. Sign up at [Mailgun](https://www.mailgun.com)
2. Add your domain and verify DNS records
3. Create a route:
   - Filter: `match_recipient("reports@yourdomain.com")`
   - Action: `forward("https://trading-hook.yourdomain.com/webhook")`
4. Forward your trading report emails to `reports@yourdomain.com`

#### Option B: Using SendGrid

1. Create SendGrid account
2. Configure Inbound Parse
3. Set webhook URL: `https://trading-hook.yourdomain.com/webhook`

#### Option C: IMAP Polling (Fallback)

If webhooks aren't available, N8N can poll your email inbox:

1. Open N8N: `http://localhost:5678`
2. Import workflow: `services/n8n/workflows/email-monitor.json`
3. Configure IMAP trigger with your email credentials

### Telegram Bot Setup

```bash
# 1. Create bot
# Talk to @BotFather on Telegram
# Send: /newbot
# Follow instructions to get token

# 2. Get your Chat ID
# Talk to @userinfobot on Telegram
# It will show your chat ID

# 3. Add to .env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Domain and SSL Setup

#### Using Traefik (Included)

1. Point your domain to your server IP
2. Update `.env`:
   ```bash
   WEBHOOK_URL=https://trading-hook.yourdomain.com
   ACME_EMAIL=your@email.com
   ```
3. Traefik will automatically get Let's Encrypt SSL certificate

#### Using Nginx (Alternative)

See `infrastructure/nginx/README.md` for Nginx setup instructions.

### N8N Workflow Import

1. Access N8N: `http://localhost:5678`
2. Login with credentials from `.env`
3. Go to Workflows → Import from File
4. Import all workflows from `services/n8n/workflows/`
5. Activate workflows

## 🔧 Configuration

### Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| N8N | http://localhost:5678 | Workflow orchestration |
| AI Analyzer API | http://localhost:8000 | Report analysis service |
| Email Webhook | http://localhost:8001 | Email processing & validation |
| Playwright Scraper API | http://localhost:8002 | Browser automation & scraping |
| Health Monitoring API | http://localhost:8003 | Health checks & error logging |
| Notification API | http://localhost:8004 | Multi-channel notification delivery |
| PostgreSQL | localhost:5432 | Data persistence |

### Environment Variables

See `.env.example` for complete list of configuration options.

Key variables:

- `ANTHROPIC_API_KEY` or `GROQ_API_KEY` - Choose your AI provider
- `TRADING_PORTAL_USERNAME/PASSWORD` - Your trading portal credentials
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `SMTP_*` - Email sending configuration

## 📚 Usage

### Manual Report Processing

You can manually trigger report processing:

```bash
# Test webhook
curl -X POST http://localhost:5678/webhook/test \
  -H "Content-Type: application/json" \
  -d '{
    "from": "test@example.com",
    "subject": "Trading Report",
    "body": "Report available at: https://portal.example.com/report/123"
  }'
```

### API Documentation

Each service has interactive API docs:

- AI Analyzer: http://localhost:8000/docs
- Email Webhook: http://localhost:8001/docs
- Playwright Scraper: http://localhost:8002/docs
- Health Monitoring: http://localhost:8003/docs
- Notifications: http://localhost:8004/docs

**Unified Notification Service Endpoints:**
- `POST /api/v1/notify` - Send notification to one or more channels
- `POST /api/v1/notify/batch` - Send batch notifications
- `GET /api/v1/delivery-status/{id}` - Query delivery status
- `GET /api/v1/delivery-stats` - Aggregate delivery statistics
- `GET /api/v1/channels` - List enabled channels and status
- `GET /health` - Service health check

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific service tests
cd services/playwright-scraper && pytest

# Run with coverage
make test-cov

# Integration tests
make test-integration
```

## 📊 Monitoring

### Health Checks

```bash
# Check all services
make health

# View logs
make logs

# Service-specific logs
make logs-service SERVICE=playwright-scraper
```

### Metrics Dashboard (Optional)

Start monitoring stack:

```bash
make monitor
```

Access dashboards:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

### Health Monitoring Service

The system includes a dedicated health monitoring service that continuously checks all services and generates alerts:

```bash
# View aggregate health status of all services
curl http://localhost:8003/api/v1/health/status

# Get recent CRITICAL errors
curl 'http://localhost:8003/api/v1/health/errors?severity=CRITICAL&hours=24'

# Trigger manual health check for a specific service
curl -X POST http://localhost:8003/api/v1/health/check/ai-analyzer

# View health monitoring logs
make logs-service SERVICE=health-monitoring
```

**Features:**
- Continuous service health monitoring (every 60 seconds)
- Automatic alert generation with batching to prevent alert storms
- Persistent health check history and error logs
- Configurable data retention policies
- CRITICAL error detection with automatic email alerts

See `HEALTH_MONITORING.md` in `/docs` for detailed operations manual.

## 🛠️ Development

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Type checking
make typecheck

# Fix auto-fixable issues
make fix
```

### Local Development

```bash
# Start with hot reload
make dev

# Open shell in a service
make shell SERVICE=playwright-scraper

# Database shell
make db-shell
```

### Adding Features

1. Modify service code in `services/<service>/src/`
2. Code changes auto-reload in development mode
3. Add tests in `services/<service>/tests/`
4. Run `make test` to verify
5. Update N8N workflows if needed

## 🔒 Security Best Practices

1. **Never commit `.env` file** - Use `.env.example` as template
2. **Rotate API keys regularly** - Update in `.env` and restart services
3. **Use strong passwords** - For database and N8N
4. **Enable firewall** - Only expose necessary ports
5. **Keep services updated** - Run `docker-compose pull` regularly
6. **Monitor logs** - Check for suspicious activity
7. **Backup database** - Run `make db-backup` daily

## 💾 Backup and Restore

### Backup

```bash
# Backup database
make db-backup

# Backup N8N workflows
docker cp trading-n8n:/home/node/.n8n/workflows ./backups/n8n-workflows-$(date +%Y%m%d)
```

### Restore

```bash
# Restore database
make db-restore

# Choose backup file when prompted
```

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check logs
make logs

# Verify .env is configured
cat .env

# Clean and restart
make clean
make dev-build
```

### Playwright Scraping Fails

```bash
# Check service logs
make logs-service SERVICE=playwright-scraper

# Test manually
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://portal.example.com/report/123",
    "credentials": {
      "username": "your_username",
      "password": "your_password"
    }
  }'
```

### AI Analysis Not Working

```bash
# Verify API key
echo $ANTHROPIC_API_KEY

# Check service logs
make logs-service SERVICE=ai-analyzer

# Test API connectivity
curl -X POST http://localhost:8001/health
```

### Notifications Not Sending

```bash
# Check notification service
make logs-service SERVICE=notification-service

# Test notification service health
curl http://localhost:8003/health

# Check channel status
curl http://localhost:8003/api/v1/channels

# Query delivery status of a notification
curl http://localhost:8003/api/v1/delivery-status/{notification_id}

# View delivery statistics
curl http://localhost:8003/api/v1/delivery-stats

# Verify Telegram bot
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"

# Test SMTP connectivity
telnet ${SMTP_HOST} ${SMTP_PORT}

# Check database for failed notifications
make db-shell
# Then run: SELECT * FROM notifications WHERE status = 'failed' ORDER BY created_at DESC LIMIT 10;
```

## 📁 Project Structure

```
trading-report/
├── agent-os/                      # Standards & product documentation
│   ├── product/                   # Product mission, roadmap, tech stack
│   ├── specs/                     # Implementation specs & tasks
│   └── standards/                 # Code standards (backend, testing)
├── database/                      # Database migrations & schemas
│   ├── migrations/                # 13 sequential SQL migrations
│   ├── maintenance/               # Database maintenance scripts
│   └── schemas/
├── docs/                          # Project documentation
│   ├── CLAUDE.md                  # AI assistant instructions
│   ├── DOCUMENTATION.md           # Master documentation index
│   ├── HEALTH_MONITORING.md       # Operations manual
│   └── USERS_MANUAL.md            # User guide
├── services/                      # Microservices
│   ├── email-webhook/             # Email processing with security validation
│   ├── playwright-scraper/        # Browser automation & scraping
│   ├── ai-analyzer/               # Report analysis
│   ├── notification-service/      # Multi-channel notifications
│   ├── health-monitoring/         # Health checks & alerting
│   └── credential-service/        # Credential storage (optional)
├── scripts/                       # Utility scripts
├── docker-compose.yml             # Docker orchestration
├── Makefile                       # Development commands (40+ targets)
├── README.md                      # This file
└── .env.example                   # Configuration template
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and test: `make test`
4. Commit: `git commit -m 'Add amazing feature'`
5. Push: `git push origin feature/amazing-feature`
6. Open Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

- Issues: GitHub Issues
- Documentation: `/docs` folder
- Email: your@email.com

## 🗺️ Roadmap

### ✅ Completed (Phases 1-11)
- [x] Email webhook service & email parsing
- [x] Secure credential storage & management
- [x] Playwright browser automation
- [x] Report content extraction & scraping
- [x] PostgreSQL schema & data persistence
- [x] AI report analysis with Groq/Anthropic API
- [x] **Unified notification service** (email + Telegram with retry & rate limiting)
- [x] Email notification delivery with SMTP integration
- [x] Telegram notification delivery with Bot API
- [x] **Webhook endpoint security** (IP whitelisting, signature validation, rate limiting, IP bans)
- [x] **Health monitoring & error logging** (continuous health checks, alert batching, automatic alerts)
- [x] N8N workflow integration & orchestration
- [x] Comprehensive documentation & operator manuals

### 🚧 In Progress

### 📋 Planned (Future Phases)
- [ ] Support for multiple trading portals
- [ ] Additional notification channels (SMS, Slack, Discord)
- [ ] Advanced pattern recognition in reports
- [ ] Historical trend analysis
- [ ] Mobile app for notifications
- [ ] Multi-user support
- [ ] Custom AI model training
- [ ] Real-time dashboard

## ⚡ Performance Tips

1. **Use Redis for caching** - Already configured
2. **Limit concurrent scrapes** - Set `MAX_CONCURRENT_SCRAPES=3` in `.env`
3. **Optimize images** - Set lower resolution in scraper config
4. **Prune old data** - Set up cron job to delete old reports
5. **Scale services** - Increase replicas in `docker-compose.yml`

```yaml
# Example: Scale playwright service
playwright-scraper:
  deploy:
    replicas: 3
```

## 📞 Contact

Your Name - [@yourtwitter](https://twitter.com/yourtwitter)
Project Link: [https://github.com/yourusername/trading-report-automation](https://github.com/yourusername/trading-report-automation)
