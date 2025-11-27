# Specification: Playwright Browser Automation

## Goal
Build a Playwright-based scraping service that authenticates to protradingskills.com, extracts trading report content including text, HTML, and TradingView chart images, and returns structured JSON responses for downstream processing.

## User Stories
- As a trading report system, I want to automatically extract content from password-protected portal URLs so that I can analyze reports without manual intervention
- As a downstream service, I want to receive structured content with base64-encoded images so that I can store and process reports without managing external file dependencies

## Specific Requirements

**Browser Automation Service Setup**
- FastAPI application exposing POST /api/v1/scrape endpoint for scraping requests
- Health check endpoint at GET /health returning service status and version
- Headless Chromium browser with 1920x1080 viewport, no-sandbox and disable-dev-shm-usage args
- Fresh browser instance per request (launch, scrape, close) with async context manager pattern
- Docker container based on mcr.microsoft.com/playwright/python with Chromium pre-installed
- Service runs on port 8001 with 120-second request timeout for complete scraping workflow

**Authentication Flow for protradingskills.com**
- Navigate to https://protradingskills.com/wp-login.php as entry point
- Detect login requirement by checking for input[id="user_login"] selector presence
- Fill credentials using selectors: input[id="user_login"] for username, input[id="user_pass"] for password
- Submit form via input[id="wp-submit"] and wait for networkidle state with 30-second timeout
- Read credentials from environment variables TRADING_PORTAL_USERNAME and TRADING_PORTAL_PASSWORD
- Implement 3-retry logic for login failures with exponential backoff delays (1s, 2s, 4s)

**Content Extraction Strategy**
- Navigate to target report URL after successful login, wait for networkidle with 60-second timeout
- Extract page title from article h2 selector, waiting for element visibility
- Extract HTML content from div.entry-content container using inner_html()
- Remove all script tags from HTML using BeautifulSoup for security and cleanliness
- Extract plain text content from div.entry-content using inner_text()
- Parse HTML with BeautifulSoup to find all img tags and extract src URLs
- Download TradingView image URLs (e.g., https://www.tradingview.com/x/km6wgmVI/) using aiohttp with base64 encoding
- Take full-page screenshot as backup visual using Playwright screenshot() method with base64 encoding

**API Request and Response Format**
- Accept JSON request body with url (required string), optional username, password, and credential_id fields
- Return success response with: success (true), url, title, html_content, text_content, report_images array (objects with url, base64, width, height), screenshot_base64
- Return error response with: success (false), url, error message string, error_type classification, empty content fields
- Use Pydantic models for request validation and response serialization
- Include metadata in response for debugging: processing timestamp, browser version, extraction duration

**Error Handling and Retry Logic**
- Retry login failures 3 times with exponential backoff (1s, 2s, 4s) for transient network issues
- Fail immediately on navigation errors (404, timeout) without retries to avoid wasting resources
- Log all errors with structured context including URL, error message, stack trace, and request ID
- Continue extraction on individual image download failures, logging skipped images without breaking pipeline
- Ensure browser cleanup in finally block using async context manager pattern
- Return partial content on extraction errors rather than complete failure

**Credential Management Integration**
- Primary credential source: environment variables for single-portal MVP scope
- Support optional credential_id parameter for future integration with credential service (Item 2)
- Never log credentials or include in error messages, apply redaction to sensitive fields
- Validate credential presence before attempting login, fail gracefully with clear error message
- Structure code to allow easy credential service integration by replacing environment variable reads

**Logging and Observability**
- Use structlog for JSON structured logging with ISO timestamp, log level, service name, and context fields
- Implement redaction processor for sensitive keys: password, secret, token, credential, api_key, access_token
- Log key events: scrape start, login attempt, navigation, extraction completion, errors with context
- Include request-level context: URL, credential_id (if used), processing duration, success/failure status
- Set log level to INFO for production, DEBUG for development via environment variable

**Image Handling Technical Approach**
- Extract image URLs from HTML using BeautifulSoup find_all("img") to get src attributes
- Filter for TradingView URLs (contains "tradingview.com") for special handling
- Download external images asynchronously using aiohttp with 30-second timeout per image
- Encode downloaded image bytes to base64 with data URI prefix (data:image/png;base64,...)
- Capture full-page screenshot using Playwright page.screenshot(full_page=True) as fallback
- Structure image objects with url, base64 data, width, and height attributes in response array

**Performance and Resource Management**
- Set page load timeout to 60 seconds to handle slow portal responses
- Set login navigation timeout to 30 seconds for authentication flow
- Use networkidle wait strategy to ensure dynamic content fully loads before extraction
- Close browser in finally block to prevent resource leaks on errors
- Limit concurrent scraping via Docker resource constraints (2GB memory limit)
- No session pooling in MVP; weekly report volume does not require optimization

**Docker Configuration and Deployment**
- Base image: mcr.microsoft.com/playwright/python:v1.40.0-jammy with Chromium bundled
- Install dependencies: fastapi, playwright, beautifulsoup4, pydantic, python-dotenv, aiohttp, uvicorn
- Copy application code and expose port 8001 for service-to-service communication
- Run uvicorn server with host 0.0.0.0 and port 8001 as container CMD
- Mount .env file for environment variables in docker-compose.yml
- Include health check in docker-compose: HTTP GET /health with 30-second interval

## Existing Code to Leverage

**refs/scraper.py - Working Login and Extraction Flow**
- Async context manager pattern with __aenter__ and __aexit__ for browser lifecycle management
- Chromium launch configuration with headless mode, no-sandbox args, and 1920x1080 viewport
- Complete login flow for protradingskills.com with correct selectors and networkidle wait strategy
- Content extraction logic using article h2 for title and div.entry-content for HTML/text
- BeautifulSoup script cleaning implementation to remove script tags from HTML content

**refs/playwright-service/scraper.py - Screenshot and Generic Structure**
- Full-page screenshot capture using page.screenshot(full_page=True) with base64 encoding
- Generic scraping function structure with async playwright context manager
- Try-except-finally pattern ensuring browser cleanup on errors
- Image data structure with type and base64 data fields for response payload

**refs/playwright-service/main.py - FastAPI Service Structure**
- FastAPI application setup with health check endpoint and scrape POST endpoint
- Pydantic request model with url, username, password, and credential_id fields
- Credential service integration pattern for fetching encrypted credentials from database
- Structured logging configuration and error handling with HTTPException responses

**refs/playwright-service/utils/logger.py - Structured Logging**
- Structlog configuration with JSON renderer and ISO timestamp processor
- Redaction processor to sanitize sensitive keys (password, secret, token, credential, api_key, access_token)
- get_logger() function for obtaining configured logger instances in modules
- Consistent log event structure with contextvars merging for request context

**refs/playwright-service/utils/crypto.py - Credential Decryption**
- CredentialManager class using Fernet symmetric encryption for credential security
- decrypt_credentials() method returning (username, password) tuple from encrypted string
- Environment variable SECRET_KEY reading for encryption key management
- Error handling for invalid encryption keys and decryption failures

## Out of Scope
- Multiple portal support with generic login detection or configuration tables (deferred to Phase 3+)
- PostgreSQL database storage of scraped content (handled by Item 4: Report Content Extraction & Scraping)
- Report versioning, audit logs, and structured metadata extraction (handled by Item 4)
- Browser session pooling or persistent sessions across requests (deferred to Phase 5 performance optimization)
- CAPTCHA or two-factor authentication handling (not required for protradingskills.com portal)
- Redis caching of scraped content or credentials (deferred to Phase 3+)
- Parallel scraping with job queue system (deferred to Phase 3+)
- Rate limiting per portal or proxy rotation strategies (deferred to Phase 3+)
- Portal metadata configuration table for custom selectors per portal (deferred to Phase 3+)
- Advanced retry strategies beyond exponential backoff (e.g., circuit breaker patterns)
