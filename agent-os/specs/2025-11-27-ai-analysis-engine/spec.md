# Specification: AI Analysis Engine

## Goal
Analyze extracted trading report content using LLM (Claude or Groq) to generate executive summaries, extract structured trading signals, identify market insights, and assign confidence scores. Store minimal analysis results in PostgreSQL for downstream notification delivery.

## User Stories
- As a trader, I want the system to analyze trading reports and extract actionable buy/sell signals with confidence scores so I can make informed trading decisions quickly
- As a system operator, I want flexible AI provider configuration (Anthropic or Groq) with automatic fallback so that service remains resilient during provider outages
- As a developer, I want structured API responses with raw content separated from analysis results so I can audit signal extraction and re-analyze reports

## Specific Requirements

**AI Provider Architecture**
- Support both Anthropic Claude and Groq APIs as configurable providers
- Check ANTHROPIC_API_KEY environment variable first; fall back to GROQ_API_KEY if not present
- Track which provider was used in each analysis result
- Do NOT store failed analyses; proceed to fallback keyword-matching extraction instead
- Return degraded response with fallback-extracted signals when LLM API fails (timeout, rate limit, invalid response)

**Analysis Output Structure**
- Generate 200-300 word executive summary from extracted report text
- Extract trading signals as structured JSON array with action/symbol/prices/confidence
- Identify market insights as list of key observations from report
- List all symbols/tickers mentioned in report
- Extract price targets mentioned for each symbol
- Assign confidence score to each signal (0.0-1.0 scale using simple 3-tier model)

**Trading Signal Model**
- Each signal contains: action (BUY/SELL/HOLD), symbol, entry_price, target_price, stop_loss, timeframe, confidence_score
- Entry price: price at which signal recommends opening position (if mentioned)
- Target price: price where signal recommends taking profit
- Stop loss: price where signal recommends cutting losses
- Timeframe: trading duration (short-term, medium-term, long-term)
- Confidence score: 0.9 for explicit recommendation, 0.6 for implied/pattern-based, 0.3 for passing mention

**LLM API Integration**
- Use async/await for all API calls to avoid blocking
- Implement 30-second timeout on LLM API calls; trigger fallback if exceeded
- Detect rate limiting errors and gracefully degrade to fallback
- Handle invalid API responses (malformed JSON, unexpected structure)
- Log failures with report_id and provider name for debugging

**Fallback Keyword Extraction**
- Implement simple keyword-matching extractor for use when LLM fails
- Extract symbols: search for common ticker patterns (e.g., AAPL, BTC, SPY)
- Extract signals: match keywords like "buy", "sell", "hold", "strong buy", "weak sell"
- Extract price targets: search for price mentions ($ prefix, numbers in specific range)
- Return signal array even if incomplete (prioritize resilience over perfection)

**Database Schema**
- Store analysis results in existing `analyses` table (id, report_id, summary, key_trades, ai_provider, created_at, etc.)
- Foreign key relationship to reports table; cascade delete on report removal
- Index on report_id for query performance
- Store trading_signals as JSONB for flexible querying
- Do NOT create separate records for failed analyses

**API Endpoint: POST /api/v1/analyze**
- Request: `{"report_id": "uuid", "raw_extracted_text": "string"}`
- Response: `{"report_id", "api_provider", "summary", "trading_signals", "market_insights", "symbols_mentioned", "price_targets", "raw_extracted_text"}`
- Return 200 on success (both LLM and fallback); 400 on bad input; 500 on fatal errors
- Include api_provider field to show which method was used (anthropic, groq, or fallback_keyword)

**Response Format**
- Keep raw_extracted_text field separate in response (for audit trail)
- Include api_provider field for transparency (shows which LLM generated analysis)
- trading_signals: array of signal objects with all required fields
- Return empty arrays for insights/symbols/targets if none identified (do not return null)
- All price fields as floats (null if not mentioned)

**Error Handling**
- Wrap LLM API calls in try-catch; log detailed error context (report_id, provider, error message)
- If LLM fails, do NOT raise exception; instead use fallback keyword extraction
- Log fallback extraction trigger at WARNING level with reason
- If fallback also fails (invalid input), return 400 with clear error message
- Never return incomplete/corrupted signal data; validate response shape before returning

**Configuration Management**
- Create Config class (following playwright-scraper pattern) to load env variables
- Load ANTHROPIC_API_KEY, GROQ_API_KEY, ANALYSIS_TIMEOUT (default 30s), LOG_LEVEL, SERVICE_PORT
- Validate that at least one API key (Anthropic or Groq) is configured at startup
- Use class properties for easy testing and environment override

**Custom Exception Hierarchy**
- AnalysisError (base class for all analysis-related errors)
- LLMError (API call failures, timeouts, rate limits)
- InvalidResponseError (malformed API response)
- ConfigurationError (missing required environment variables)
- FallbackExtractionError (fallback keyword extraction failed)

**Service Structure**
- Create FastAPI app with lifespan context manager for startup/shutdown logging
- Include router with /api/v1/analyze endpoint
- Add /health endpoint returning service status
- Add CORS middleware for service-to-service communication
- Keep config, models, exceptions, routes separated into different files

**Logging Strategy**
- Log all analysis attempts with report_id, extracted content length, provider selected
- Log LLM API calls with provider, model, tokens used (if available)
- Log fallback extraction triggers with reason (API failure, timeout, etc.)
- Use structured logging with context fields (report_id, provider, duration_ms)
- Log errors with full traceback for debugging

## Existing Code to Leverage

**Config Class Pattern (services/playwright-scraper/src/config.py)**
- Use same Config class approach: load environment variables at startup, provide get_config() function
- Follow property-based structure for easy testing and documentation
- Implement validate_config() to check required fields at initialization
- Support optional fields with sensible defaults

**Pydantic Models for Validation (services/playwright-scraper/src/models.py)**
- Create request model (AnalysisRequest) with report_id and raw_extracted_text fields
- Create response models (AnalysisSuccessResponse, AnalysisErrorResponse)
- Use field_validator decorators for input validation
- Follow naming convention: RequestName, SuccessResponseName, ErrorResponseName

**FastAPI Route Structure (services/playwright-scraper/src/api/routes.py)**
- Create APIRouter with @router.post and @router.get decorators
- Use metadata() to create response metadata (request_id, duration, timestamp)
- Return structured response objects (Pydantic models)
- Include request_id in all responses for correlation

**Custom Exception Pattern (services/playwright-scraper/src/utils/exceptions.py)**
- Create exception module with custom exception classes inheriting from Exception
- Use exception types for targeted error handling in routes
- Include error_type field in error responses for client-side handling

**Async/Await Pattern (services/playwright-scraper/src/main.py)**
- Use async functions for all I/O operations (API calls, database)
- Use @asynccontextmanager for lifespan event handling
- Follow async pattern in route handlers for concurrent request handling

**Logging Pattern (services/playwright-scraper/src/utils/logger.py)**
- Use Python logging module with structured format
- Include timestamp, log level, service name, and contextual fields
- Create logger per module using get_logger(__name__)

## Out of Scope
- Trend analysis across multiple reports or time-series correlation
- Portfolio-level aggregation or risk assessment across positions
- Analyst credibility scoring or source attribution analysis
- Multi-report comparison or position conflict detection
- Real-time market data integration or live price feeds
- Backtesting or historical performance tracking of signals
- Advanced machine learning models for signal generation
- Caching or optimization of analysis results (Phase 3+)
- Recursive analysis of related reports or parent-child relationships
- Custom prompt templates per report type or portal
