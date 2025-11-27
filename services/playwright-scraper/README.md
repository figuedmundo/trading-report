# Playwright Scraper Service

Browser automation service for scraping trading reports from password-protected portals.

## Overview

This service provides a FastAPI-based HTTP API for automated scraping of trading reports from protradingskills.com. It handles:

- Portal authentication with credential management
- Page content extraction (title, HTML, plain text)
- Image downloading and base64 encoding
- Full-page screenshot capture
- Structured error handling with retry logic

## Quick Start

### Setup

1. Copy environment variables:
```bash
cp .env.example .env
```

2. Edit `.env` with your portal credentials:
```bash
TRADING_PORTAL_USERNAME=your_username
TRADING_PORTAL_PASSWORD=your_password
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running Locally

```bash
# Install playwright browsers
playwright install chromium

# Start the service
uvicorn src.main:app --reload --port 8001
```

The service will be available at `http://localhost:8001`

### Docker

```bash
# Build image
docker build -t playwright-scraper .

# Run container
docker run -p 8001:8001 --env-file .env playwright-scraper
```

## API Endpoints

### POST /api/v1/scrape

Scrape a trading report from a portal URL.

**Request:**
```json
{
  "url": "https://protradingskills.com/report/123"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "url": "https://protradingskills.com/report/123",
  "title": "Report Title",
  "html_content": "<div>...</div>",
  "text_content": "Report text...",
  "report_images": [
    {
      "url": "https://www.tradingview.com/x/...",
      "base64": "data:image/png;base64,...",
      "width": 1595,
      "height": 902
    }
  ],
  "screenshot_base64": "data:image/png;base64,...",
  "metadata": {
    "timestamp": "2025-11-26T10:30:00Z",
    "browser_version": "1.40.0",
    "extraction_duration_ms": 5000,
    "request_id": "uuid"
  }
}
```

**Error Response (200 with success=false):**
```json
{
  "success": false,
  "url": "https://protradingskills.com/report/123",
  "error": "Login failed after 3 retries",
  "error_type": "LoginError",
  "html_content": "",
  "text_content": "",
  "report_images": [],
  "metadata": {...}
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "playwright-scraper",
  "version": "0.1.0"
}
```

## Configuration

Set environment variables in `.env` file:

- `TRADING_PORTAL_USERNAME` - Portal login username (required)
- `TRADING_PORTAL_PASSWORD` - Portal login password (required)
- `SERVICE_PORT` - Service port (default: 8001)
- `LOG_LEVEL` - Logging level: INFO, DEBUG (default: INFO)
- `PLAYWRIGHT_HEADLESS` - Run browser headless (default: true)

## Architecture

### Browser Lifecycle

Browser instance is created fresh for each request:
1. Launch Chromium with 1920x1080 viewport
2. Navigate to login page
3. Perform authentication with retry logic (3 retries, exponential backoff: 1s, 2s, 4s)
4. Navigate to target report URL
5. Extract content (title, HTML, text, images)
6. Download TradingView chart images
7. Capture full-page screenshot
8. Close browser and cleanup resources

### Timeouts

- Page load timeout: 60 seconds
- Login timeout: 30 seconds
- Image download timeout: 30 seconds per image
- Request timeout: 120 seconds (complete workflow)

### Error Handling

- **LoginError**: Login failures retry 3x with exponential backoff, then fail
- **NavigationError**: Navigation failures fail immediately without retries
- **ExtractionError**: Content extraction failures return partial data
- **ImageDownloadError**: Failed image downloads are skipped but don't fail request
- **CredentialError**: Missing credentials fail immediately

All errors are logged with request context including request ID for distributed tracing.

### Logging

JSON structured logs with:
- ISO timestamp
- Log level
- Service name
- Request ID (for correlation)
- Message and context fields
- Automatic credential redaction

## Development

### File Structure

```
src/
├── main.py              # FastAPI app entry point
├── config.py            # Configuration management
├── models.py            # Pydantic request/response models
├── browser.py           # BrowserManager with login flow
├── extractor.py         # Content extraction logic
├── api/
│   └── routes.py        # HTTP endpoint handlers
└── utils/
    ├── logger.py        # Structured logging
    ├── exceptions.py    # Custom exception classes
    ├── image_handler.py # Image download and encoding
    └── screenshot.py    # Screenshot capture
tests/
├── conftest.py          # Pytest fixtures
└── test_*.py            # Unit tests
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_browser_lifecycle.py -v
```

## Integration with N8N

This service is designed to integrate with N8N workflow orchestration:

1. N8N receives webhook with trading report email
2. N8N calls POST /api/v1/scrape with report URL
3. Service returns structured response with content and images
4. N8N routes based on `success` flag and `error_type` field
5. Response fed to AI analyzer service for content analysis

## Performance

- Fresh browser per request (no session pooling)
- Expected processing time: 10-20 seconds per report
- Concurrent requests handled by separate browser instances
- Docker memory limit: 2GB per container

## Security

- Credentials read from environment variables only
- Credentials never logged or exposed in error messages
- Automatic credential redaction in all logs
- No sensitive data stored in response payloads
- Input validation on all request parameters
- Content sanitization (script tag removal)

## Monitoring

Check service health:
```bash
curl http://localhost:8001/health
```

View service logs:
```bash
docker logs -f <container_id>
```

## Troubleshooting

### Service won't start
- Check `.env` file is properly configured
- Verify port 8001 is not in use
- Check Docker image built successfully

### Login fails
- Verify credentials in `.env` are correct
- Check portal is accessible
- Review logs for specific error details

### Images not downloading
- Check internet connectivity
- Verify TradingView URLs are still valid
- Review image download timeout settings

### Browser crashes
- Check Docker memory limit
- Monitor system resources
- Review browser logs for errors

## Dependencies

- FastAPI 0.104.1
- Playwright 1.40.0
- BeautifulSoup4 4.12.2
- Pydantic 2.5.0
- aiohttp 3.9.0
- uvicorn 0.24.0

## References

- Specification: `/agent-os/specs/2025-11-26-playwright-browser-automation/spec.md`
- CLAUDE.md: Project conventions and architecture
- Standards: `/agent-os/standards/` directory
