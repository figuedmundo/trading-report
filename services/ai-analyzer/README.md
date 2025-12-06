# AI Analysis Engine

FastAPI service for analyzing trading reports using LLM (Claude or Groq) with fallback keyword extraction.

## Overview

The AI Analysis Engine accepts extracted trading report content and uses either Anthropic Claude or Groq API to:
- Generate 200-300 word executive summaries
- Extract trading signals (BUY/SELL/HOLD) with confidence scores
- Identify market insights and symbols mentioned
- Extract price targets for each symbol

If the LLM API fails (timeout, rate limit, API error), the service gracefully falls back to keyword-based extraction, ensuring resilience.

## Quick Start

### 1. Install Dependencies

```bash
cd services/ai-analyzer
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the service root:

```bash
# AI Provider (use one or both for fallback)
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk-...

# Service Configuration
SERVICE_PORT=8002
LOG_LEVEL=INFO
ANALYSIS_TIMEOUT=30

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/trading_reports
```

### 3. Start the Service

```bash
# Using uvicorn directly
python -m uvicorn src.main:app --host 0.0.0.0 --port 8002

# Or using Docker
docker build -t ai-analyzer .
docker run -p 8002:8002 --env-file .env ai-analyzer
```

### 4. Verify Health

```bash
curl http://localhost:8002/health
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | None | Anthropic Claude API key (primary) |
| `GROQ_API_KEY` | None | Groq API key (fallback) |
| `SERVICE_PORT` | 8002 | Service port |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ANALYSIS_TIMEOUT` | 30 | LLM API timeout in seconds |
| `DATABASE_URL` | None | PostgreSQL connection string |

## API Endpoints

### POST /api/v1/analyze

Analyze a trading report and extract signals.

**Request Headers (Optional):**
- `X-AI-Provider`: Override configured AI provider (e.g., `anthropic`, `groq`, `google`)
- `X-LLM-Model`: Override specific model (e.g., `claude-3-5-sonnet-20241022`)
- `X-Prompt-Name`: Override prompt type/template (e.g., `default`, `conservative`)

**Request Body:**
```json
{
  "report_id": "123e4567-e89b-12d3-a456-426614174000",
  "raw_extracted_text": "BTC strong buy signal with target 45000..."
}
```

**Response (Success):**
```json
{
  "report_id": "123e4567-e89b-12d3-a456-426614174000",
  "api_provider": "anthropic",
  "model_name": "claude-3-5-sonnet-20241022",
  "summary": "Executive summary of the report...",
  "trading_signals": [
    {
      "action": "BUY",
      "symbol": "BTC",
      "entry_price": 43000.0,
      "target_price": 45000.0,
      "stop_loss": 40000.0,
      "timeframe": "medium-term",
      "confidence_score": 0.9
    }
  ],
  "market_insights": [
    "Strong momentum in crypto markets",
    "Resistance forming at 450 level"
  ],
  "symbols_mentioned": ["BTC", "ETH", "SPY"],
  "price_targets": {
    "BTC": 45000.0,
    "ETH": 2500.0
  },
  "raw_extracted_text": "BTC strong buy signal..."
}
```

**Response (Error):**
```json
{
  "detail": "Invalid request body"
}
```

**Status Codes:**
- 200: Success (both LLM and fallback)
- 400: Invalid input (missing/empty fields)
- 500: Fatal error (database unavailable)

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "ai-analyzer",
  "version": "0.1.0"
}
```

## LLM Provider Selection

The service automatically selects the LLM provider based on environment variables:

1. **Checks ANTHROPIC_API_KEY first** - Uses Claude API if configured
2. **Falls back to GROQ_API_KEY** - Uses Groq if Anthropic not configured
3. **Raises ConfigurationError** - If neither is configured

### Dynamic Selection (New)

You can override the default provider, model, and prompt per request using API headers:

- `X-AI-Provider`: Force a specific provider (e.g., "groq" to use Groq even if Anthropic is default)
- `X-LLM-Model`: Force a specific model (e.g., "mixtral-8x7b-32768")
- `X-Prompt-Name`: Switch prompt strategy

## Fallback Behavior

If LLM API fails for any reason:
- Timeout (> 30 seconds)
- Rate limiting
- Invalid response
- API error

The service:
1. Logs the failure at WARNING level
2. Calls `FallbackExtractor` for keyword-based extraction
3. Returns analysis results with `api_provider: "fallback_keyword"`
4. **Does NOT** raise an exception or return error status

## Confidence Scoring

Signals are scored on a simple 3-tier model:

- **0.9** - Explicit recommendation (words like "recommend", "strong buy/sell" in close proximity)
- **0.6** - Implied/pattern-based (words like "uptrend", "support", "resistance")
- **0.3** - Passing mention (symbol + action word somewhere in text)

## Response Format

All responses include:
- `api_provider`: Which method extracted the signals (anthropic, groq, or fallback_keyword)
- `trading_signals`: Array (never null)
- `market_insights`: Array (never null)
- `symbols_mentioned`: Array (never null)
- `price_targets`: Object/dict (never null)
- Price fields: float or null (never string)

## Example Usage

### Using curl with Dynamic Headers

```bash
# Use Groq instead of default Anthropic
curl -X POST http://localhost:8002/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "X-AI-Provider: groq" \
  -d '{
    "report_id": "report-123",
    "raw_extracted_text": "BTC is showing strong buy signals. Entry at 43000, target 45000, stop loss at 40000."
  }'

# Use specific model
curl -X POST http://localhost:8002/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "X-LLM-Model: gemini-2.0-flash" \
  -d '{ ... }'
```

### Using Python

```python
import requests

headers = {
    "Content-Type": "application/json",
    "X-AI-Provider": "groq",
    "X-Prompt-Name": "conservative"
}

response = requests.post(
    "http://localhost:8002/api/v1/analyze",
    headers=headers,
    json={
        "report_id": "report-123",
        "raw_extracted_text": "BTC strong buy at 43000, target 45000..."
    }
)

analysis = response.json()
print(f"Provider used: {analysis['api_provider']}")
print(f"Summary: {analysis['summary']}")
```

## Troubleshooting

### Service won't start
- Check that at least one API key is configured (ANTHROPIC_API_KEY or GROQ_API_KEY)
- Verify DATABASE_URL is correct
- Check port 8002 is not in use

### Health check fails
```bash
# Check logs
docker logs trading-ai-analyzer

# Or if running locally
python -c "import src.main"
```

### LLM API errors
- Verify API key is valid
- Check rate limits on API provider
- Review logs for detailed error messages

### Database connection errors
- Verify PostgreSQL is running
- Check DATABASE_URL format: `postgresql://user:password@host:port/db`
- Run migrations: `psql $DATABASE_URL < ../../database/migrations/006_create_analyses_table.sql`

## Architecture

```
Request → Routes → AnalysisService → LLMAnalyzer → [Anthropic|Groq]
                                  ↓ (on failure)
                                FallbackExtractor
                                  ↓
                           ConfidenceScorer
                                  ↓
                        AnalysesRepository → PostgreSQL
```

## Testing

Run tests with pytest:

```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_llm_integration.py -v

# With coverage
pytest tests/ --cov=src
```

## Database Schema

The service stores analyses in the `analyses` table:

```sql
CREATE TABLE analyses (
    id UUID PRIMARY KEY,
    report_id UUID NOT NULL REFERENCES reports(id),
    summary TEXT NOT NULL,
    trading_signals JSONB,
    ai_provider VARCHAR(50),
    created_at TIMESTAMPTZ
);
```

## Development

### Code Structure

```
services/ai-analyzer/
├── src/
│   ├── config.py              # Configuration management
│   ├── models.py              # Pydantic models
│   ├── main.py                # FastAPI app
│   ├── utils/
│   │   ├── exceptions.py      # Custom exceptions
│   │   └── logger.py          # Structured logging
│   ├── llm/
│   │   ├── provider.py        # LLM provider abstraction
│   │   └── analyzer.py        # Analysis orchestration
│   ├── extraction/
│   │   ├── fallback.py        # Keyword extraction
│   │   └── confidence.py      # Confidence scoring
│   ├── db/
│   │   ├── connection.py      # DB connection pool
│   │   └── analyses_repository.py  # Data persistence
│   ├── services/
│   │   └── analysis_service.py    # Service orchestration
│   └── api/
│       └── routes.py          # API endpoints
└── tests/
    ├── test_llm_integration.py
    └── test_api_endpoint.py
```

### Adding Logging

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

logger.info("Message", extra={
    "report_id": "123",
    "provider": "anthropic",
    "duration_ms": 1500
})
```

### Error Handling Pattern

```python
from src.utils.exceptions import AnalysisError, LLMError

try:
    # Operation
except LLMError as e:
    logger.error(f"LLM error: {e.message}", extra={"error_code": e.error_code})
    # Fallback handling
except AnalysisError as e:
    logger.error(f"Analysis error: {e.message}")
    raise
```

## Performance Notes

- LLM timeout: 30 seconds (configurable via ANALYSIS_TIMEOUT)
- Database pool: 5-20 connections
- Fallback extraction: < 100ms
- Typical end-to-end: 2-5 seconds (LLM) or 100ms (fallback)

## Security Considerations

- API keys stored in environment variables, never logged
- Database uses parameterized queries to prevent SQL injection
- No authentication required (runs on trusted network)
- Structured logging redacts sensitive fields

## License

Part of Trading Report Monitor system.
