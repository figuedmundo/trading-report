# Tech Stack Documentation

## Overview

The Trading Report Monitor system uses a distributed, containerized architecture deployed on a homelab environment. The stack emphasizes reliability, privacy (data stays on-premise), and flexibility. All services are containerized with Docker and orchestrated via Docker Compose.

---

## Core Architecture & Orchestration

### Workflow Engine
- **N8N** (self-hosted)
  - Purpose: Visual workflow orchestration and automation
  - Role: Connects webhook trigger to scraper, AI analysis, and notification services
  - Deployment: Docker container, persistent storage for workflow definitions
  - Version: Latest stable (monitored for updates)
  - Database: N8N manages its own database within container

### Message Queue & Task Distribution
- **Redis** (optional, for advanced phases)
  - Purpose: Caching frequently accessed reports, rate limiting, session storage
  - Role: Reduces database load for repeated queries
  - Deployment: Docker container
  - Configuration: Standard Redis cache, TTL-based expiration
  - Used in: Phase 3+ for performance optimization

---

## Backend Services

### Primary Backend Language
- **Python 3.11+**
  - Primary choice for custom services (Playwright scraper, AI analyzer)
  - Rationale: Excellent ecosystem for web scraping, AI/LLM integration, async operations
  - Package Manager: `pip` / Poetry (optional for dependency management)
  - Alternative: Node.js (Express/Fastify) equally viable but Python preferred for scraper complexity

### Microservices

#### 1. Email Webhook Service
- **Framework**: FastAPI or Flask
- **Purpose**: HTTP endpoint receiving email payloads from email service provider
- **Responsibilities**:
  - Validate incoming webhook requests (signature verification, rate limiting)
  - Parse email metadata (sender, subject, body, attachments)
  - Extract report detection patterns (keyword matching, URL extraction)
  - Queue report processing task
- **Key Dependencies**:
  - FastAPI (async HTTP framework)
  - Pydantic (request validation)
  - cryptography (signature validation)
  - email-validator (email parsing)
- **Deployment**: Docker container, exposed on subdomain with TLS via Traefik

#### 2. Browser Automation & Scraper Service
- **Framework**: Python + Playwright
- **Purpose**: Handle authenticated portal access and content extraction
- **Responsibilities**:
  - Login to trading portals using provided credentials
  - Navigate to report URLs
  - Extract text, images, metadata
  - Handle dynamic JavaScript-rendered content
  - Capture TradingView charts and embedded media
  - Export structured report data
- **Key Dependencies**:
  - Playwright (browser automation)
  - Beautiful Soup 4 / Parsel (HTML parsing)
  - Pillow (image handling)
  - pytesseract / easyocr (optional, for image text extraction)
  - python-dotenv (credential management)
- **Deployment**: Docker container with Chromium browser bundle
- **Credential Handling**: Read from encrypted vault (environment variables, not code)
- **Timeout Management**: Per-portal connection timeouts; retry logic with exponential backoff

#### 3. AI Analysis Service
- **Framework**: Python + LLM API clients
- **Purpose**: Intelligent report analysis and summarization
- **Responsibilities**:
  - Call AI provider API with report text
  - Generate executive summaries (200-300 words)
  - Extract trading signals (buy/sell recommendations, symbols, price targets)
  - Identify market sentiment and key insights
  - Format analysis for notification delivery
- **AI Provider Options** (choose one, support both initially):
  - **Anthropic Claude** (preferred for nuanced analysis)
    - Model: claude-3-5-sonnet-20241022 (latest)
    - API Client: anthropic Python package
    - Cost: ~$0.003 per report (estimates for typical prompt)
  - **Groq** (faster inference, lower cost)
    - Model: mixtral-8x7b-32768 or latest available
    - API Client: groq Python package
    - Cost: ~$0.0005 per report (free tier available)
- **Key Dependencies**:
  - anthropic (Anthropic API client)
  - groq (Groq API client)
  - langchain (optional, for prompt management)
- **Deployment**: Docker container, async API calls with timeout handling
- **Error Handling**: Fallback to generic summary on API failure; retry with exponential backoff

#### 4. Notification Service
- **Framework**: Python (async)
- **Purpose**: Multi-channel report delivery
- **Responsibilities**:
  - Format and send email summaries via SMTP
  - Send formatted messages to Telegram
  - Track notification delivery status
  - Implement retry logic for failed deliveries
- **Email Integration**:
  - Protocol: SMTP (TLS/SSL)
  - Dependencies: smtplib (Python stdlib), email (stdlib)
  - External: User's SMTP provider (Gmail, custom mail server, etc.)
  - Template Engine: Jinja2 (for HTML/text formatting)
- **Telegram Integration**:
  - API: Telegram Bot API
  - Client: python-telegram-bot or httpx (direct API calls)
  - Authentication: Bot token stored in encrypted vault
  - Formatting: HTML or Markdown for rich text
- **Deployment**: Docker container
- **Delivery Confirmation**: Log delivery status in PostgreSQL; retry failed deliveries in queue

---

## Data Storage & Persistence

### Primary Database
- **PostgreSQL 15+** (self-hosted)
  - Purpose: Persistent storage for all application data
  - Deployment: Docker container with persistent volume mount
  - Backup Strategy: Daily automated backups with pg_dump; stored locally and optionally to S3
  - Replication: Optional master-replica setup for high availability (Phase 3+)

### Database Schema Components
- **reports** table: Raw extracted report content, metadata, source attribution, timestamps
- **analyses** table: AI-generated summaries, trading signals, confidence scores
- **notifications** table: Delivery logs (email, Telegram), timestamps, success/failure status
- **credentials** table: Encrypted portal login credentials, per-report overrides
- **audit_logs** table: All system events for compliance and troubleshooting
- **email_sources** table: Configured email addresses and associated configuration
- **trading_signals** table: Extracted signals with symbols, direction, price targets, timeframes
- **portal_configs** table: Portal URLs, login endpoints, extraction patterns per portal

### ORM / Query Builder
- **SQLAlchemy** (Python)
  - Purpose: Database abstraction and object-relational mapping
  - Alternative: psycopg2 (raw SQL) or Alembic (migrations)
  - Rationale: Provides schema flexibility and type safety

### Backup & Recovery
- **Strategy**: Daily automated PostgreSQL dumps via cronjob
- **Retention**: Keep 7 days of backups locally; archive to cold storage monthly
- **Recovery Testing**: Monthly restore validation to verify backup integrity

---

## API & Integration Layer

### External API Integration
- **Anthropic API** (for report analysis)
  - Endpoint: api.anthropic.com
  - Authentication: Bearer token (API key)
  - Rate Limits: Respect per-minute and per-day quotas
  - Fallback: Switch to Groq if Anthropic unavailable

- **Groq API** (alternative/backup AI)
  - Endpoint: api.groq.com
  - Authentication: API key
  - Cost: Lower than Anthropic, faster inference
  - Fallback: Switch to Anthropic if Groq rate limited

- **Email Service Provider Webhook**
  - Receives: Email metadata when messages arrive
  - Protocol: HTTPS with signature verification
  - Options: Mailgun, SendGrid webhook relay, or custom IMAP polling
  - Signature Validation: Cryptographic verification of incoming requests

- **Telegram Bot API**
  - Endpoint: api.telegram.org/botXXX
  - Authentication: Bot token (generated via @BotFather)
  - Methods: sendMessage, parseMode HTML
  - Rate Limits: Respect 30 messages/second global limit

- **SMTP Server** (for email sending)
  - Protocol: SMTP with STARTTLS
  - Configuration: User-provided (Gmail, custom mail server, etc.)
  - Credentials: Stored encrypted in environment or vault

---

## Security & Credential Management

### Encryption & Secrets
- **Method**: Environment variables with dotenv + encryption for sensitive values
- **Vault Alternative**: HashiCorp Vault or similar for Phase 3+
- **Files to Protect**:
  - `.env` file (never committed to git)
  - Trading portal credentials
  - API keys (Anthropic, Groq, Telegram)
  - SMTP passwords
  - Database credentials

### Secret Rotation
- **Credentials**: Manually updated in environment; consider automated rotation in Phase 4
- **API Keys**: Monitor Anthropic/Groq for expired keys; implement alerts
- **Database Passwords**: Document change procedure; coordinate with backup system

### Data Privacy
- **On-Premise Only**: All sensitive data (credentials, reports, analyses) stay within homelab network
- **No Third-Party Data Sharing**: Trading credentials never sent to external services
- **Encrypted Database**: Optional encryption-at-rest for PostgreSQL (Phase 3+)
- **Network Isolation**: Database not exposed directly; only accessible from application containers

---

## Deployment & Infrastructure

### Container Orchestration
- **Docker** (27.3+)
  - Purpose: Containerize all services
  - Containers: Webhook service, scraper, AI analyzer, notification service, PostgreSQL, Redis, N8N
  - Registry: Docker Hub (pull) or local registry for air-gapped setups

- **Docker Compose** (2.29+)
  - Purpose: Multi-container orchestration and local deployment
  - File: docker-compose.yml (includes all services and networking)
  - Networks: Isolated Docker network for container-to-container communication
  - Volumes: Persistent storage for PostgreSQL, N8N, backups

### Reverse Proxy & TLS
- **Traefik** (optional, for production homelab)
  - Purpose: Reverse proxy with automatic TLS certificate management
  - Benefit: Routes external traffic to webhook endpoint securely
  - Alternative: Nginx with Let's Encrypt for manual setup
  - Configuration: Docker Compose labels for automatic service discovery
  - Certificates: Let's Encrypt via Traefik ACME integration

### Homelab Deployment
- **Hardware Requirements**:
  - CPU: 4+ cores (8+ recommended)
  - RAM: 8GB minimum (16GB+ recommended)
  - Storage: 50GB+ (includes PostgreSQL, backups, log history)
  - Network: Stable internet connection; expose single HTTPS endpoint for webhook

- **Network Configuration**:
  - DNS: Custom subdomain (e.g., trading.figuedmundo.com) pointing to homelab IP
  - Firewall: Open port 443 (HTTPS) for webhook; block all others
  - Reverse Proxy: Traefik or Nginx handles SSL termination and port forwarding
  - Internal Network: Docker Compose isolated network for service communication

- **Monitoring & Logs**:
  - Log Aggregation: stdout/stderr from containers captured by Docker
  - Log Viewing: `docker-compose logs -f [service]`
  - Monitoring Stack: Optional Prometheus + Grafana (Phase 2+)
  - Health Checks: Docker health checks on each container

---

## Development & Testing

### Backend Development
- **Language**: Python 3.11+
- **Virtual Environment**: venv or poetry
- **Testing Framework**: pytest
  - Unit tests: Service logic, parsing, validation
  - Integration tests: E2E workflow with mock emails and portals
  - Fixtures: Mock Playwright, mock AI responses
- **Code Quality**:
  - Linting: ruff, flake8
  - Type Checking: mypy
  - Code Formatting: black
  - Pre-commit Hooks: Optional for development quality gates

### Local Development Workflow
```bash
# Clone and setup
git clone <repo>
cd trading-report
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start local development stack
docker-compose -f docker-compose.dev.yml up

# Run individual service
python -m services.email_webhook
```

### CI/CD Pipeline (GitHub Actions / GitLab CI)
- Run pytest on every push
- Lint and type check code
- Build Docker images for main branch
- Deploy to homelab on tag (manual trigger)

---

## Browser Automation Specifics

### Playwright Configuration
- **Language Binding**: Python (playwright package)
- **Browser**: Chromium (bundled with playwright)
- **Headless Mode**: Enabled (no GUI needed)
- **Timeouts**:
  - Page load: 30 seconds
  - Navigation: 30 seconds
  - Login form submission: 10 seconds
  - Screenshot capture: 5 seconds
- **Anti-Detection**:
  - User-Agent rotation (optional)
  - Viewport size variation (optional)
  - Disable headless detection (if portal checks for it)

### Error Handling
- Login failures: Retry up to 3x with exponential backoff
- Timeouts: Fall back to cached version if available
- JavaScript errors: Log but continue (many modern sites have benign JS errors)
- CAPTCHA: Manual intervention required (alert user); store for retry

### Performance
- Connection pooling: Reuse browser contexts across requests
- Parallel processing: Multiple Playwright instances via job queue (Phase 3+)
- Caching: Cache extracted images and text in PostgreSQL

---

## Monitoring & Observability

### Health Checks
- Each service exposes `/health` endpoint
- Kubernetes-style readiness probes (via Docker Compose health checks)
- Periodic webhook to confirm notification delivery

### Metrics & Logging
- **Application Logs**:
  - Format: JSON (structured logging with python-json-logger)
  - Level: INFO (production), DEBUG (development)
  - Retention: 30 days in container logs; archive older logs

- **Database Metrics**:
  - Connection pool usage
  - Query performance (slow query log)
  - Backup success/failure

- **API Metrics**:
  - Response times (Anthropic, Groq, Telegram)
  - Error rates and retry counts
  - Rate limit status

### Alerting
- Email alerts: Critical errors sent to admin
- Dashboard: Optional Grafana dashboard showing system health
- Log Analysis: Optional ELK stack for searchable logs (Phase 3+)

---

## Optional Enhancements (Phase 3+)

### Caching Layer
- Redis for caching expensive operations
- Session storage for Playwright browser contexts
- Rate limiting for webhook endpoint

### Advanced Orchestration
- Kubernetes: For multi-instance deployments
- Apache Airflow: Alternative to N8N for more complex workflows
- Celery: Task queue for distributed processing

### Advanced Analytics
- ClickHouse: Time-series database for analytics
- Apache Superset: Data visualization platform

### Message Queues
- RabbitMQ: For high-volume report processing
- Apache Kafka: For event streaming and replay

---

## Dependency Summary

### Python Core
```
fastapi / flask
pydantic
playwright
beautifulsoup4
sqlalchemy
python-dotenv
anthropic / groq
python-telegram-bot
requests / httpx
pytest
```

### Infrastructure
```
Docker 27.3+
Docker Compose 2.29+
PostgreSQL 15+
Redis (optional)
Traefik (optional)
N8N (workflow engine)
```

### External Services
```
Anthropic API or Groq API (AI analysis)
Telegram Bot API (notifications)
SMTP Server (email notifications)
Email Webhook Provider (incoming reports)
```

---

## Justification: N8N vs. Custom Application

### Decision: Hybrid Approach (N8N + Custom Services)

**N8N Handles:**
- Workflow orchestration and visual workflow management
- Email trigger logic and basic data transformation
- Service-to-service integration (webhook -> scraper -> AI -> notifications)

**Custom Services Handle:**
- Complex Playwright browser automation
- Advanced report parsing and content extraction
- Specialized AI prompt engineering for trading analysis
- Credential encryption and secure storage
- Custom business logic for report detection

**Why This Approach?**
1. **N8N is not ideal for** complex scraping, Playwright, and AI integration (limited environment, dependencies)
2. **Custom Python services are better for** browser automation, advanced NLP, and specialized logic
3. **N8N excels at** connecting services, visual workflows, and configuration management
4. **Best of both:** Leverage N8N for orchestration while having full flexibility in custom services

**Alternative: Pure Custom Application**
- Build entire backend in Python/Node.js without N8N
- Pros: More control, simpler dependencies, easier to test
- Cons: Must build workflow UI and scheduling engine from scratch
- Recommended if: Team prefers code-based configuration or needs extreme customization

---

## Maintenance & Updates

### Regular Updates
- Docker images: Monthly review and pull latest base images
- Python dependencies: Quarterly updates (check for security patches)
- N8N: Follow releases; upgrade on minor versions, test on patch
- PostgreSQL: Annual or as needed (backwards compatible updates)

### Version Pinning
- Docker base images: Pin to specific minor versions (e.g., python:3.11.8-slim)
- Python requirements: Pin dependencies in requirements.txt or poetry.lock
- Database: Document current version; plan upgrade path

### Backward Compatibility
- Database migrations: Always test on backup before production
- API changes: Maintain backward compatibility for 1 major version
- Credential format: Never change without migration strategy
