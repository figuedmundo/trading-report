# Playwright Scraper Service - Local Development Guide

## Overview

The Playwright Scraper Service is a FastAPI-based web scraping service that uses Playwright to extract content from password-protected trading reports on ProTradingSkills.com.

## Prerequisites

- Python 3.11+ (Currently tested with Python 3.13.1)
- pip
- Virtual environment support

## Local Setup & Installation

### 1. Create and Activate Virtual Environment

```bash
cd services/playwright-scraper
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
```

### 4. Configure Environment Variables

Make sure the `.env` file in the project root contains:

```bash
# Playwright Scraper Configuration
SCRAPER_HEADLESS=false  # Set to true for production
SCRAPER_DEBUG=true
SCRAPER_TIMEOUT_MS=30000

# Trading Portal Credentials
TRADING_PORTAL_URL=https://protradingskills.com
TRADING_PORTAL_USERNAME=your-email@gmail.com
TRADING_PORTAL_PASSWORD=your-password
```

## Running the Service Locally

### Start the Service

```bash
cd services/playwright-scraper
source venv/bin/activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8002
```

The service will start on `http://localhost:8002`

### API Endpoints

#### Health Check
```bash
GET http://localhost:8002/health
```

#### Scrape Report
```bash
POST http://localhost:8002/api/v1/scrape
Content-Type: application/json

{
  "url": "https://protradingskills.com/analysis/report-url/",
  "username": "optional-override-username",
  "password": "optional-override-password"
}
```

### Example Usage

#### Using curl:

```bash
curl -X POST "http://localhost:8002/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://protradingskills.com/analysis/operacion-rapida-en-una-accion-explosiva/"}'
```

#### Using Python requests:

```python
import requests

response = requests.post(
    "http://localhost:8002/api/v1/scrape",
    json={"url": "https://protradingskills.com/analysis/report-url/"}
)

data = response.json()
print(f"Title: {data['title']}")
print(f"Content length: {len(data['text_content'])} chars")
```

## Debugging

### View Browser Window

When `SCRAPER_HEADLESS=false` is set in `.env`, you'll see the Chrome browser window open on your machine, allowing you to observe:

- Login process
- Navigation to report URL
- Content extraction
- Any errors that occur

### Check Logs

The service outputs detailed JSON logs to stdout:

```bash
# Start service and view logs
python -m uvicorn src.main:app --host 0.0.0.0 --port 8002 --log-level debug
```

### Common Issues

#### 1. Empty Content Extraction

**Symptom:** `title: "Acceder"`, empty `html_content` or `text_content`

**Cause:** Browser is stuck on login page - session isn't persisting

**Solution:** Check `src/browser.py` login verification logic (line 172)

#### 2. Authentication Failures

**Symptom:** Login not working, redirected back to login page

**Possible Causes:**
- Incorrect credentials in `.env`
- ProTradingSkills changed login form structure
- Session cookies not being saved properly

**Debug Steps:**
1. Set `SCRAPER_HEADLESS=false` to watch browser
2. Check `TRADING_PORTAL_USERNAME` and `TRADING_PORTAL_PASSWORD` in `.env`
3. Review logs for login attempt details

#### 3. Timeout Errors

**Symptom:** `Timeout exceeded` errors during extraction

**Solution:** Increase timeout in `.env`:
```bash
SCRAPER_TIMEOUT_MS=60000  # Increase to 60 seconds
```

## Project Structure

```
services/playwright-scraper/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── browser.py           # Playwright browser & authentication
│   ├── extractor.py         # Content extraction with fallback selectors
│   ├── api/
│   │   └── routes.py        # API endpoint definitions
│   └── utils/
│       ├── logger.py        # Structured logging
│       └── exceptions.py    # Custom exceptions
├── tests/                   # pytest test files
├── venv/                    # Python virtual environment (git-ignored)
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker container definition
└── README.md               # This file
```

## Running Tests

```bash
cd services/playwright-scraper
source venv/bin/activate
pytest -v
```

## Docker vs Local Development

### Docker (Production)
```bash
cd /path/to/trading-report
docker-compose up playwright-scraper
```

### Local (Development)
```bash
cd services/playwright-scraper
source venv/bin/activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8002 --reload
```

**Key Differences:**
- Local: See browser window when `SCRAPER_HEADLESS=false`
- Local: Faster iteration with `--reload` flag
- Docker: Consistent environment, closer to production

## Next Steps

1. Fix authentication session persistence issue in `src/browser.py`
2. Add proper login verification (check if still on login page after submission)
3. Implement cookie persistence across page navigations
4. Add retry logic with exponential backoff
5. Implement health check database queries

## Additional Resources

- **Playwright Documentation:** https://playwright.dev/python/
- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **Project Main README:** See project root directory

## Troubleshooting

### Python 3.13 Compatibility Issues

If you encounter build errors with `greenlet` or `pydantic-core`:

```bash
# Install compatible versions
pip install pydantic==2.12.5 pydantic-core==2.41.5
```

### Playwright Browser Not Found

```bash
# Reinstall browsers
playwright install chromium --force
```

### Port Already in Use

```bash
# Find process using port 8002
lsof -i :8002

# Kill the process
kill -9 <PID>
```

## Support

For issues or questions:
1. Check the logs: `docker-compose logs playwright-scraper`
2. Review the main project documentation
3. Check ProTradingSkills.com for any changes to their login flow
