# Spec Requirements: Playwright Browser Automation

## Initial Description
Build Playwright automation to handle trading portal login, navigate to provided URL, and maintain session state across multiple page interactions. This is Phase 1, Roadmap Item #3.

**Context from Roadmap:**
- Precedes Item #4 (Report Content Extraction & Scraping) which handles storage to PostgreSQL
- Follows Item #2 (Secure Credential Storage & Management - already completed)
- Part of MVP to establish end-to-end email-to-report pipeline

## Requirements Discussion

### First Round Questions

**Q1: Login Handling - Should this support multiple trading portals with generic login detection, or focus on a single portal with hardcoded selectors?**
**Answer:** Single portal only - the one in `refs/scraper.py` (protradingskills.com with hardcoded selectors). No need for generic detection or portal metadata configuration.

**Q2: Session Management - Should the browser persist across requests (session pooling) or launch fresh per request?**
**Answer:** Fresh browser per request (launch → login → navigate → extract → close). Reports are weekly, so no persistent browser needed.

**Q3: 2FA Handling - Does the trading portal require two-factor authentication or CAPTCHA challenges?**
**Answer:** NOT required. No 2FA handling needed.

**Q4: Image Extraction Strategy - Should we extract TradingView image URLs from DOM, download them, or take full-page screenshots?**
**Answer:** User provided example image URL: `<img src="https://www.tradingview.com/x/km6wgmVI/" width="1595" height="902">` and asked for technical recommendation.

**Technical Recommendation (Spec Writer Decision):**
- Extract TradingView image URLs from DOM (via Playwright selectors or BeautifulSoup)
- Download external images (TradingView URLs) to avoid link expiration
- Take full-page screenshot as backup
- Store images as base64 in database for simplicity (avoid file system management)
- **Rationale:** TradingView chart URLs may expire; downloading ensures persistence. Base64 encoding simplifies storage in PostgreSQL JSONB fields without separate blob storage.

**Q5: Error Handling - What retry logic and timeout strategy should be implemented?**
**Answer:** User requested technical recommendation.

**Technical Recommendation (Spec Writer Decision):**
- 3 retries for login failures with exponential backoff (1s, 2s, 4s)
- Fail-fast for navigation/timeout errors (no retries for dead links)
- 60s page load timeout
- 30s login timeout
- **Rationale:** Login failures may be transient (network issues), but bad URLs should fail immediately to avoid wasting resources.

**Q6: API Parameters - Should the API support portal-specific overrides (timeout, skip login flag, viewport size)?**
**Answer:**
- Portal-specific overrides: NO (user doesn't understand, not needed for single portal)
- Timeouts: Use implicit waits
- Skip login flag: NO (user doesn't know, not needed)
- Viewport: Headless browser (1920x1080 as in existing code)

**Q7: Content Storage - Should this service handle database persistence or just return raw content via API?**
**Answer:** User thought roadmap item #4 handles storage. User said "if you want to do here please go ahead."

**Technical Recommendation (Spec Writer Decision):**
This item (#3) should focus on scraping and returning raw content via API. Item #4 (Report Content Extraction & Scraping) will handle storage to PostgreSQL and advanced extraction logic. Keep separation of concerns.

**Scope Decision:**
- Item #3 (this spec): Playwright automation, login, content extraction, return via API response
- Item #4 (future): PostgreSQL storage, report versioning, audit logs, structured metadata extraction

**Q8: Portal Metadata Configuration - Should we support configuration table for multiple portals or hardcode single portal?**
**Answer:** NO - not needed for single portal.

**Q9: Visual Assets - Do you have design mockups, wireframes, or screenshots?**
**Answer:** NO - the existing `refs/scraper.py` was already working for login and navigation. User has working reference code.

### Existing Code to Reference

**Similar Features Identified:**
- Feature: Working Playwright scraper implementation
- Path: `/Users/edmundo.figueroaherbas@medirect.com.mt/projects/personal/trading-report/refs/scraper.py`

**Key Implementation Details from Reference Code:**

1. **Login Flow (Working):**
   - Portal: https://protradingskills.com/wp-login.php
   - Username selector: `input[id="user_login"]`
   - Password selector: `input[id="user_pass"]`
   - Submit button: `input[id="wp-submit"]`
   - Wait strategy: `wait_for_load_state('networkidle', timeout=60000)`

2. **Browser Configuration (Working):**
   - Headless: `True`
   - Args: `['--no-sandbox', '--disable-dev-shm-usage']`
   - Viewport: `1920x1080`
   - User-Agent: Custom via `Config.USER_AGENT`

3. **Content Extraction (Working):**
   - Title selector: `article h2`
   - Content container: `div.entry-content`
   - HTML extraction: `inner_html()`
   - Text extraction: `inner_text()`
   - Script removal: BeautifulSoup to remove `<script>` tags

4. **Image Extraction (Broken - Needs Fix):**
   - Current method: `_get_images()` using BeautifulSoup
   - Issue: Extraction logic incomplete
   - Fix needed: Extract TradingView URLs, download images, encode to base64

5. **Async Context Manager Pattern (Working):**
   - Uses `__aenter__` and `__aexit__` for resource management
   - Ensures browser cleanup on exit

**Components to Reuse:**
- Entire login flow and selectors
- Browser launch configuration
- Async context manager pattern
- HTML/text extraction logic
- Script cleaning with BeautifulSoup

**Backend Logic to Reference:**
- Error handling structure (try/except with logger)
- Response format: `{"success": bool, "url": str, "title": str, "html_content": str, "text_content": str, "report_images": list}`

### Follow-up Questions
None required. All clarifications obtained from user responses.

## Visual Assets

### Files Provided:
No visual assets provided.

### Visual Insights:
Not applicable - user has working reference code in `refs/scraper.py`.

## Requirements Summary

### Functional Requirements

**Core Functionality:**
1. **Browser Automation Service:**
   - Accept POST request with report URL
   - Launch headless Chromium browser per request
   - Navigate to protradingskills.com login page
   - Perform login with credentials from environment variables
   - Navigate to target report URL
   - Extract content (title, HTML, text, images)
   - Return structured JSON response
   - Clean up browser resources

2. **Login Flow:**
   - Navigate to https://protradingskills.com/wp-login.php
   - Check if login required (detect `input[id="user_login"]`)
   - Fill username and password fields
   - Submit login form
   - Wait for navigation completion (networkidle state)

3. **Content Extraction:**
   - Extract page title from `article h2` selector
   - Extract HTML content from `div.entry-content`
   - Remove all `<script>` tags from HTML
   - Extract plain text content
   - Extract all image URLs from DOM
   - Download TradingView image URLs
   - Encode downloaded images to base64
   - Take full-page screenshot as backup

4. **Error Handling:**
   - Retry login failures 3 times with exponential backoff (1s, 2s, 4s)
   - Fail immediately on navigation errors (bad URLs)
   - Return structured error response with details
   - Log all errors with context (URL, error message, traceback)

5. **API Response Format:**
   ```json
   {
     "success": true,
     "url": "https://example.com/report",
     "title": "Market Analysis Report",
     "html_content": "<div>...</div>",
     "text_content": "Report text...",
     "report_images": [
       {
         "url": "https://www.tradingview.com/x/km6wgmVI/",
         "base64": "data:image/png;base64,iVBORw0KG...",
         "width": 1595,
         "height": 902
       }
     ],
     "screenshot_base64": "data:image/png;base64,..."
   }
   ```

6. **Error Response Format:**
   ```json
   {
     "success": false,
     "url": "https://example.com/report",
     "error": "Login failed after 3 retries",
     "error_type": "LoginError",
     "html_content": "",
     "text_content": "",
     "report_images": []
   }
   ```

### Technical Requirements

**1. Service Architecture:**
- Framework: FastAPI (async HTTP framework)
- Language: Python 3.11+
- Deployment: Docker container with Chromium
- Port: 8001 (exposed for service-to-service communication)
- Health check endpoint: GET /health

**2. API Endpoints:**

**POST /api/v1/scrape**
- Request body:
  ```json
  {
    "url": "https://protradingskills.com/report/123"
  }
  ```
- Response: JSON with success/error structure (see above)
- Timeout: 120 seconds (allow for login + navigation + extraction)

**GET /health**
- Response:
  ```json
  {
    "status": "ok",
    "service": "playwright-scraper",
    "version": "0.1.0"
  }
  ```

**3. Playwright Configuration:**
- Browser: Chromium (bundled with playwright)
- Headless mode: True
- Viewport: 1920x1080
- Args: `['--no-sandbox', '--disable-dev-shm-usage']`
- User-Agent: Custom (match reference code)
- Page load timeout: 60 seconds
- Login timeout: 30 seconds
- Element wait timeout: 10 seconds

**4. Credential Management:**
- Read credentials from environment variables:
  - `TRADING_PORTAL_USERNAME`
  - `TRADING_PORTAL_PASSWORD`
- Never log credentials
- Fail gracefully if credentials missing

**5. Dependencies:**
```python
fastapi==0.104.1
playwright==1.40.0
beautifulsoup4==4.12.2
pydantic==2.5.0
python-dotenv==1.0.0
httpx==0.25.2  # for downloading images
uvicorn==0.24.0  # ASGI server
```

**6. Logging:**
- Logger: Python `logging` module
- Format: JSON structured logging
- Level: INFO (production), DEBUG (development)
- Fields: timestamp, level, service, url, action, error (if applicable)

**7. Docker Configuration:**
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**8. Error Handling Strategy:**
- **Login Errors:** Retry 3x with exponential backoff (1s, 2s, 4s)
- **Timeout Errors:** Fail immediately, return error response
- **Navigation Errors:** Fail immediately, return error response
- **Extraction Errors:** Log but continue (return partial content)
- **Image Download Errors:** Log but continue (skip failed images)

### Reusability Opportunities

**From Existing Code (`refs/scraper.py`):**
1. **Async context manager pattern** for browser lifecycle management
2. **Login selectors and flow** (already working for protradingskills.com)
3. **Content extraction selectors** (`article h2`, `div.entry-content`)
4. **BeautifulSoup script cleaning** logic
5. **Response structure** format
6. **Error handling patterns** (try/except with logging)

**Integration Points:**
1. **Credential Service (Item #2 - Completed):**
   - Read credentials from environment variables
   - Future: May call credential service API for encrypted retrieval

2. **Item #4 (Report Content Extraction & Scraping - Future):**
   - Item #4 will consume this service's API
   - Item #4 will handle PostgreSQL storage
   - Item #4 will extract structured metadata (symbols, signals, dates)

### Scope Boundaries

**In Scope (Item #3 - This Spec):**
- Playwright browser automation service
- Login to protradingskills.com portal
- Content extraction (title, HTML, text, images)
- TradingView image download and base64 encoding
- Full-page screenshot capture
- FastAPI REST endpoint
- Error handling and retry logic
- Docker containerization
- Health check endpoint
- Structured JSON response format

**Out of Scope (Deferred to Item #4 or Later):**
- PostgreSQL database storage (Item #4)
- Report versioning and audit logs (Item #4)
- Structured metadata extraction (symbols, signals, dates) (Item #4)
- Multiple portal support (Phase 3+)
- Portal configuration management (Phase 3+)
- Browser session pooling (Phase 5 - performance optimization)
- CAPTCHA/2FA handling (not needed)
- Redis caching (Phase 3+)
- Parallel scraping with job queue (Phase 3+)

**Future Enhancements (Not Part of MVP):**
- Generic login detection for multiple portals
- Portal metadata configuration table
- Persistent browser sessions
- Rate limiting per portal
- Proxy rotation
- User-Agent rotation

### Technical Considerations

**1. Integration with N8N Workflow:**
- N8N will orchestrate workflow: Email webhook → Scraper → AI Analyzer → Notifications
- N8N will call POST /api/v1/scrape with report URL
- N8N will pass response to AI Analyzer service

**2. Credential Security:**
- Credentials stored in environment variables (`.env` file)
- Never logged or exposed in error messages
- Docker secrets for production deployment

**3. Performance:**
- Fresh browser per request (no session pooling in MVP)
- Expected processing time: 10-20 seconds per report
- Weekly report volume: Low (1-3 reports per week)
- No need for optimization in Phase 1

**4. Browser Resource Management:**
- Always close browser in `finally` block
- Use async context manager pattern
- Docker memory limit: 2GB per container

**5. Image Handling Strategy:**
- Extract image URLs from DOM using Playwright selectors
- Download images using httpx library (async HTTP client)
- Convert to base64 for database storage
- Capture full-page screenshot using Playwright `screenshot()` method
- Store both individual images and screenshot in response

**6. Testing Strategy:**
- Unit tests: Mock Playwright browser responses
- Integration tests: Test against real protradingskills.com (staging environment)
- Fixtures: Mock HTML responses, mock image downloads
- Test coverage target: 80%+

**7. Monitoring:**
- Log all scraping attempts with timestamps
- Track success/failure rates
- Monitor response times
- Alert on repeated login failures

**8. Technology Stack Alignment:**
Per `agent-os/product/tech-stack.md`:
- Python 3.11+ (confirmed)
- FastAPI (confirmed)
- Playwright (confirmed)
- Docker + Docker Compose (confirmed)
- Async operations (confirmed)

**9. Code Standards Compliance:**
Per `agent-os/standards/`:
- Follow `global/coding-style.md`: Black formatting, type hints, naming conventions
- Follow `backend/api.md`: REST endpoint patterns, error responses
- Follow `testing/test-writing.md`: pytest fixtures, mocking strategies
- Follow `global/error-handling.md`: Structured error responses, logging context
- Follow `global/validation.md`: Pydantic request/response validation

**10. Similar Code Patterns to Follow:**
- Async/await pattern from reference code
- Context manager pattern for resource cleanup
- Structured logging with context fields
- Error response format matching system conventions
