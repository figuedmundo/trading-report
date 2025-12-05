# Trading Report Automation System

## Project Overview

This is a comprehensive microservices-based system designed to automate the processing of trading reports. It monitors emails, securely receives webhooks, scrapes dynamic content using Playwright, analyzes reports using AI (Anthropic Claude or Groq), and delivers unified notifications via Email and Telegram.

### Key Technologies
- **Core**: Python, Docker, Docker Compose
- **Orchestration**: N8N
- **Database**: PostgreSQL
- **AI**: Anthropic Claude 3.5 Sonnet / Groq
- **Browser Automation**: Playwright
- **API Framework**: FastAPI (inferred from service structure)

## Architecture

The system consists of the following containerized services:

- **postgres** (5432): Primary data persistence with audit trails.
- **n8n** (5678): Workflow orchestration and visual automation.
- **ai-analyzer** (8000): AI service for intelligent report analysis.
- **email-webhook** (8001): Security layer for handling incoming email webhooks (IP allowlisting, rate limiting).
- **playwright-scraper** (8002): Headless browser service for scraping trading portals.
- **health-monitoring** (8003): Continuous system health checks and error alerting.
- **notification-service** (8004): Unified delivery for Email (SMTP) and Telegram.
- **gmail-bridge** (8005): IMAP polling service for Gmail integration.

## Building and Running

The project uses a `Makefile` to standardize common operations.

### Initial Setup
1.  Create the environment file and build images:
    ```bash
    make setup
    ```
2.  **Important**: Edit the generated `.env` file with your credentials (API keys, database passwords, SMTP settings, etc.).

### Running the System
-   **Development Mode** (logs attached):
    ```bash
    make dev
    ```
-   **Production Mode** (detached):
    ```bash
    make prod
    ```
-   **Stop All Services**:
    ```bash
    make stop
    ```
-   **Clean Start** (removes containers and volumes):
    ```bash
    make clean
    ```

### Database Management
-   **Initialize Database**: `make db-init`
-   **Access Shell**: `make db-shell`
-   **Backup**: `make db-backup`
-   **Restore**: `make db-restore`

## Development Conventions

### Code Quality
The project enforces strict Python code quality standards. Run these commands before committing:

-   **Format** (Black):
    ```bash
    make format
    ```
-   **Lint** (Flake8, Pylint):
    ```bash
    make lint
    ```
-   **Type Check** (Mypy):
    ```bash
    make typecheck
    ```

### Testing
-   **Run All Tests**:
    ```bash
    make test
    ```
-   **Specific Test Suites**:
    -   Schema Validation: `make test-schema`
    -   Data Flow: `make test-data`
    -   Content Extraction: `make test-content-extraction`

### Service Logs
To view logs for a specific service:
```bash
make logs-service SERVICE=<service_name>
# Example: make logs-service SERVICE=ai-analyzer
```

## Directory Structure

-   `services/`: Source code for individual microservices.
-   `database/`: SQL migrations, schemas, and maintenance scripts.
-   `agent-os/`: Project specifications and product planning documents.
-   `docs/`: Detailed documentation and user manuals.
-   `docker-compose.yml`: Service orchestration configuration.
-   `Makefile`: Command-line task runner.
