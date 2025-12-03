## Project Overview

This is a Trading Report Automation System that automates the process of monitoring emails for trading reports, scraping the reports using Playwright, analyzing them with an AI service (Claude or Groq), and sending notifications through various channels (Email, Telegram).

The project is a microservices-based architecture using Docker and Docker Compose. The services include:

*   **postgres**: The PostgreSQL database for data persistence.
*   **n8n**: The N8N workflow orchestration tool.
*   **email-webhook**: A service to handle incoming email webhooks, providing a security layer.
*   **playwright-scraper**: The service that uses Playwright to scrape web pages.
*   **ai-analyzer**: The service that integrates with AI models (Anthropic/Groq) to analyze data.
*   **notification-service**: The service responsible for sending notifications via SMTP (email) and Telegram.

## Building and Running

The project uses a `Makefile` to simplify the build and run process.

### Setup

To set up the project, run:

```bash
make setup
```

This will create a `.env` file from the `.env.example` template and build the Docker images. You will need to edit the `.env` file with your credentials.

### Running the application

To run the application in development mode (with logs), use:

```bash
make dev
```

To run the application in production mode (detached), use:

```bash
make prod
```

### Stopping the application

To stop the application, use:

```bash
make stop
```

### Cleaning up

To stop and remove all containers and volumes, use:

```bash
make clean
```

### Testing

To run all tests, use:

```bash
make test
```

## Development Conventions

*   **Configuration**: All configuration is done through the `.env` file.
*   **Code Style**: The project uses `black` for code formatting, `flake8` and `pylint` for linting, and `mypy` for type checking. You can run these checks with the following commands:
    *   `make format`
    *   `make lint`
    *   `make typecheck`
*   **Database Migrations**: Database migrations are located in the `database/migrations` directory and are applied automatically on startup.
*   **Dependencies**: Python dependencies are managed in `requirements.txt` files for each service.
