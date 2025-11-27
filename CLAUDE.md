# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**AI IMPORTANT**
- Always use context7 when I need code generation, setup or configuration steps, or library/API documentation. This means you should automatically use the Context7 MCP tools to resolve library id and get library docs without me having to explicitly ask.


## Project Overview

**Trading Report Monitor** is an automated system that captures trading reports from emails, extracts content from password-protected web portals using browser automation, analyzes them with AI, and delivers summaries via email and Telegram.

**Key Architectural Pattern**: Microservices + N8N orchestration
- Services handle specific concerns (scraping, analysis, notifications)
- N8N manages workflow orchestration and webhook triggers
- Docker Compose for local deployment
- PostgreSQL for persistent storage with audit trails

## Quick Start Commands

### Development & Setup
```bash
# View available make commands
make help

# Start services with logs visible
make dev

# Start services in background (production-like)
make prod

# Build images
make build
```

### Testing & Code Quality
```bash
# Run all tests
make test

# Run tests for a specific service
cd services/playwright-scraper && pytest

# Code formatting
make format

# Linting
make lint

# Type checking
make typecheck
```

### Database & Debugging
```bash
# Open PostgreSQL shell
make db-shell

# Backup database
make db-backup

# View service logs (all or specific)
make logs
make logs-service SERVICE=playwright-scraper

# Check service health
make health
```

### Common Workflows
```bash
# Cleanup everything and rebuild
make clean && make dev-build

# Run a single test file
cd services/playwright-scraper && pytest tests/test_scraper.py -v

# Interactive shell in a running service
make shell SERVICE=playwright-scraper

# Test webhook manually
curl -X POST http://localhost:5678/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"from":"test@example.com","subject":"Trading Report","body":"Report at: https://portal.example.com/report/123"}'
```

## Architecture Deep Dive

### Directory Structure
```
trading-report/
├── agent-os/                          # Documentation & standards
│   ├── product/                       # Product docs (mission, roadmap, tech-stack)
│   ├── specs/                         # Implementation specs
│   └── standards/                     # Code standards (backend, frontend, testing)
├── playwright-service/                # Reference Playwright scraper code
├── database/                          # Database migrations & schemas
├── refs/                              # Reference files (configs, examples)
├── services/                          # [Will contain] Main microservices
│   ├── email-webhook/                # Email event handler
│   ├── playwright-scraper/            # Portal content extraction
│   ├── ai-analyzer/                   # Report analysis & summarization
│   └── notification-service/          # Email & Telegram delivery
├── docker-compose.yml                 # Service orchestration
├── Makefile                           # Development commands
├── README.md                          # User-facing documentation
└── .env.example                       # Environment variables template
```

### Data Flow & Service Integration

```
1. Email Event
   └─> Webhook Service (validates, parses email)
       └─> N8N Workflow (orchestrates)
           ├─> [Parallel] Scraper Service (extracts content)
           │   └─> PostgreSQL (stores raw report)
           ├─> AI Analyzer Service (analyzes content)
           │   └─> PostgreSQL (stores analysis)
           └─> Notification Service (sends alerts)
               ├─> Email (SMTP)
               └─> Telegram (Bot API)
```

### Key Technology Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Web scraping ecosystem, LLM integration, async support |
| Framework | FastAPI | Async HTTP, auto-documentation, Pydantic validation |
| Browser Automation | Playwright | Handles authentication, dynamic content, TradingView charts |
| Database | PostgreSQL 15+ | ACID compliance, audit trails (append-only), JSON support |
| AI Provider | Anthropic Claude OR Groq | User-configurable; Claude for nuance, Groq for speed/cost |
| Orchestration | N8N | Visual workflows, built-in error handling, webhook UI |
| Deployment | Docker Compose | Homelab-friendly, reproducible, single domain with Traefik |

### Critical Architecture Constraints

1. **Privacy-First**: All data stays on-premise (no cloud APIs except AI)
2. **Webhook-Driven**: Real-time email processing (not polling)
3. **Append-Only Database**: Full audit trail for compliance
4. **Idempotent Operations**: Safe to retry without duplicates
5. **Single User**: Authentication not required (run on trusted network)

## Code Standards & Patterns

Reference the `agent-os/standards/` directory for detailed guidelines:

### Global Standards
- **Coding Style** (`global/coding-style.md`): Naming conventions, formatting, linting rules
- **Conventions** (`global/conventions.md`): File organization, imports, constants
- **Validation** (`global/validation.md`): Input validation at system boundaries
- **Commenting** (`global/commenting.md`): When to comment (explain "why", not "what")

### Backend Standards
- **API Design** (`backend/api.md`): REST endpoint patterns, versioning, error responses
- **Models** (`backend/models.md`): Database model structure, relationships, fields
- **Queries** (`backend/queries.md`): Efficient SQL, N+1 prevention, index usage
- **Migrations** (`backend/migrations.md`): Schema changes, versioning, rollback strategy

### Testing Standards
- **Test Writing** (`testing/test-writing.md`): Unit vs integration, mocking, fixtures

## Service Development Patterns

### Adding a New Microservice

1. **Create service structure**:
   ```
   services/my-service/
   ├── src/
   │   ├── __init__.py
   │   ├── main.py          # FastAPI app
   │   └── api/
   │       └── routes.py    # Endpoint definitions
   ├── tests/
   │   ├── __init__.py
   │   └── test_*.py        # pytest test files
   ├── Dockerfile
   └── requirements.txt
   ```

2. **Core service template** (FastAPI):
   ```python
   from fastapi import FastAPI
   from pydantic import BaseModel

   app = FastAPI(title="My Service", version="0.1.0")

   @app.get("/health")
   async def health():
       return {"status": "ok"}

   @app.post("/api/v1/process")
   async def process(request: MyRequest):
       # Business logic here
       return {"result": "..."}
   ```

3. **Add to docker-compose.yml**:
   - Define service container
   - Map ports (avoid conflicts)
   - Mount volumes for hot-reload in dev
   - Set environment variables
   - Add health check

4. **Add Make targets**:
   ```makefile
   test-my-service:
       cd services/my-service && pytest -v

   shell-my-service:
       docker-compose exec my-service bash
   ```

### Credential & Secret Management

**DO NOT**:
- Commit `.env` files
- Store secrets in code
- Log credentials

**DO**:
- Use environment variables via `.env.example`
- Read from `os.environ` or use `python-dotenv`
- Encrypt sensitive DB fields (at-rest encryption)
- Use separate credentials table for trading portals
- Rotate API keys regularly

### Database Changes

1. Create migration file in `database/migrations/`:
   ```sql
   -- migration_YYYY_MM_DD_description.sql
   BEGIN;

   CREATE TABLE new_table (...);

   COMMIT;
   ```

2. Document schema in `agent-os/specs/` if architecture changes
3. Test with `make db-shell` before deploying
4. Keep migrations append-only (no destructive changes in production)

## Common Patterns & Anti-Patterns

### ✅ Recommended Patterns

**Error Handling**:
```python
# Service returns structured error response
class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None

# Log with context
logger.error("Scraping failed", extra={
    "report_id": report_id,
    "error": str(e),
    "traceback": traceback.format_exc()
})
```

**Async Operations**:
```python
# FastAPI routes should be async
@app.post("/api/v1/analyze")
async def analyze(request: AnalysisRequest):
    result = await ai_service.analyze(request.content)
    return result
```

**Database Queries**:
```python
# Use parameterized queries (prevent SQL injection)
cursor.execute("SELECT * FROM reports WHERE id = %s", (report_id,))

# Index frequently-queried fields
# Index on: id, created_at, status, email_from
```

### ❌ Anti-Patterns to Avoid

- Synchronous I/O in async code
- Hardcoded secrets in code
- Unvalidated user input
- N+1 database queries (load related data in batch)
- Overly broad exception handling (`except Exception`)
- Ignoring webhook signature validation

## Testing Strategy

### Unit Tests
- Test individual functions with mocked dependencies
- Fast execution (< 1 second per test)
- Located in `services/<service>/tests/test_*.py`

### Integration Tests
- Test service interactions (e.g., API + database)
- Use test fixtures for setup/teardown
- Run against Docker services if needed

### Example Test Structure
```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def sample_report():
    return {"id": "123", "content": "..."}

def test_scraper_extracts_content(sample_report):
    result = scraper.extract(sample_report)
    assert result["title"] is not None
    assert result["body"] is not None

@patch('services.ai_service.analyze')
def test_analyzer_handles_api_failure(mock_analyze):
    mock_analyze.side_effect = Exception("API error")
    # Test fallback behavior
```

## Performance & Monitoring

### Key Metrics to Track
- Email detection latency (target: < 30 seconds)
- Report processing time (target: < 5 minutes end-to-end)
- Notification delivery time (target: < 2 minutes)
- Service uptime (target: 99.5%)
- Database query performance (watch slow queries)

### Optimization Tips
1. Use Redis caching for frequently-accessed reports (Phase 3+)
2. Limit concurrent Playwright instances (avoid memory issues)
3. Index database fields used in WHERE clauses
4. Use connection pooling for database
5. Monitor Docker resource limits

### Debugging
```bash
# View container logs with timestamps
docker-compose logs -f --timestamps [service]

# Check service health endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health

# Inspect database queries (enable query logging)
POSTGRES_QUERY_LOG=true make dev

# Test N8N workflows in UI
http://localhost:5678/workflows
```

## Deployment & Operations

### Configuration
- All configuration via `.env` file (copy from `.env.example`)
- Sensitive values encrypted in database
- Portal-specific configs in database `portal_configurations` table

### Environment Variables Reference
```bash
# AI Provider (choose one)
ANTHROPIC_API_KEY=sk-ant-...
# OR
GROQ_API_KEY=...

# Trading Portal Credentials
TRADING_PORTAL_USERNAME=your_username
TRADING_PORTAL_PASSWORD=your_password

# Email & Notifications
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
SMTP_HOST=smtp.gmail.com
SMTP_USER=your@email.com
SMTP_PASSWORD=your_app_password

# Database
POSTGRES_PASSWORD=secure_password
DATABASE_URL=postgresql://user:password@postgres:5432/trading_reports

# Webhook
WEBHOOK_URL=https://trading-hook.yourdomain.com
```

### Backups & Recovery
```bash
# Backup
make db-backup

# Restore (interactive prompt)
make db-restore

# Backup N8N workflows
docker cp trading-n8n:/home/node/.n8n/workflows ./backups/
```

## Documentation References

For detailed information, consult:
- **Product Vision**: `agent-os/product/mission.md`
- **Roadmap & Features**: `agent-os/product/roadmap.md`
- **Technical Details**: `agent-os/product/tech-stack.md`
- **Database Schema**: `agent-os/specs/2025-11-25-postgresql-schema-data-persistence/spec.md`
- **Implementation Tasks**: See `planning/` directory for spec verification

## Common Issues & Solutions

### Service Won't Start
- Check `.env` file is configured
- Verify port conflicts: `lsof -i :8000`
- Clean and rebuild: `make clean && make dev-build`
- Check logs: `make logs`

### Playwright Scraping Fails
- Verify trading portal credentials in `.env`
- Check portal URL hasn't changed
- Look for login form selector changes
- Test manually: `curl -X POST http://localhost:8000/api/v1/health`

### AI Analysis Not Working
- Verify API key is set and valid
- Check rate limiting on AI service
- Review model name (Anthropic vs Groq)
- Look for token limit exceeded errors

### Telegram Notifications Not Sending
- Verify bot token is valid: `curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"`
- Confirm chat ID is correct
- Check network connectivity from container

## When to Use Agents (Claude Code Task Tool)

Use `Task` tool with specialized agents for:
- **Explore agent**: Understanding codebase structure, finding patterns
- **Spec-writer**: Writing detailed technical specifications
- **Implementer**: Building features following a tasks.md plan
- **Implementation-verifier**: End-to-end testing of features

Example: `Task(subagent_type='Explore', prompt='Find all webhook handlers in the codebase')`

---

**Last Updated**: November 25, 2025
**Key Contributors**: Project initiated as trading report automation system
