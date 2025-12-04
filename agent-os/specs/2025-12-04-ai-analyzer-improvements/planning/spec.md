# Specification: AI Analyzer Service Improvements

## Goal

Enhance the AI Analyzer Service to support configurable LLM models via environment variables, enable extended thinking processes with optional storage in the database, support free-form text responses with markdown-based operations extraction, and maintain backward compatibility with existing analyses while improving financial analysis quality.

## User Stories

- As a system operator, I want to configure the LLM model via a single `LLM_MODEL` environment variable (e.g., `claude-3-7-sonnet`) so that I can easily switch between different models without code changes.
- As a developer, I want the provider to be selected automatically based on the configured model name so that the system intelligently routes requests to the correct API provider.
- As a financial analyst, I want the AI to use extended thinking when processing complex trading reports so that the analysis quality and reasoning transparency improve.
- As a database administrator, I want to store extended thinking processes optionally in the database so that I can audit the AI's reasoning and reference it later if needed.
- As a system integrator, I want to parse trading operations from free-form LLM responses using markdown sections so that the system remains flexible and can handle diverse response formats.

## Specific Requirements

**Model Configuration & Provider Factory Pattern**
- Introduce single `LLM_MODEL` environment variable to specify the model name (e.g., `claude-3-7-sonnet`, `mixtral-8x7b-32768`, `gemini-2.0-flash`)
- Implement provider factory that maps model names to provider instances (Anthropic, Groq, Google Gemini)
- Validate model name at startup; fail fast with clear error if model is unsupported or no matching provider API key is configured
- Maintain backward compatibility by keeping existing provider detection (ANTHROPIC_API_KEY, GROQ_API_KEY) as fallback
- Support future provider additions (Gemini 3) without modifying core factory logic via plugin-like extensibility

**Extended Thinking Process Support**
- Add configurable budget parameter `THINKING_BUDGET_TOKENS` (default: 5000) to control extended thinking depth
- Enable extended thinking as opt-in via `ENABLE_THINKING` env var (default: false) to avoid unnecessary API costs
- Support provider-specific thinking flags (Anthropic: budget_tokens, Groq/Gemini: best-effort support)
- Log thinking process usage and token consumption for cost tracking
- Validate thinking configuration at service initialization

**Database Schema Extensions**
- Add `thinking_process` TEXT NULLABLE column to analyses table for storing extended thinking output
- Add `thinking_enabled` BOOLEAN DEFAULT false column to track whether thinking was used for this analysis
- Add `thinking_budget_tokens` INTEGER column to store the budget used for this analysis
- Add `response_format` VARCHAR(20) column to track if response came from LLM (text-based) or fallback extraction
- Create index on (thinking_enabled, created_at) for querying analyses that used extended thinking
- Migrate existing analyses as legacy with thinking_enabled=false to preserve history

**API Request/Response Format Changes**
- Accept same input format: `{"report_id": "...", "raw_extracted_text": "..."}`
- Remove forced JSON schema requirement from LLM prompts; allow natural language responses
- LLM should return free-form text with optional markdown sections for operations (## Trading Operations, ## Analysis, etc.)
- Response format: mix of free-form text analysis + optional structured trading operations
- Extend AnalysisSuccessResponse to include `thinking_process` (optional), `response_format`, and `operations_found` flag
- Maintain existing fields for backward compatibility (summary, trading_signals, market_insights, symbols_mentioned, price_targets)

**Trading Operations JSONB Storage**
- Store trading operations as JSONB array in analyses table (flexible, no rigid type validation)
- Operations schema: flexible structure supporting {symbol, action, quantity, entry_price, target_price, stop_loss, operation_type, timeframe, confidence}
- Allow operations array to be empty or null (sparse data model)
- Include `operations_found` boolean flag in response to indicate if operations were extracted
- Support operations parsing from markdown ## Trading Operations section via regex/text extraction
- Operations are optional: if no operations section in LLM response, set operations_found=false and operations=null

**Response Parsing & Markdown Extraction**
- Implement markdown section parser to extract ## Trading Operations from free-form responses
- Fallback: if no operations section found, attempt to extract structured signals from analysis text using regex patterns
- Create helper utility `parse_markdown_sections()` to extract sections by heading level (## Level 2 headings)
- Create helper utility `extract_trading_operations()` to parse operations from markdown-formatted text
- Error handling: if parsing fails, log warning and set operations_found=false (graceful degradation)
- No exceptions for parsing failures; always return valid response with operations_found flag

**Streaming & Buffering Behavior**
- Current behavior: accumulate full LLM response in memory, then return complete analysis (no streaming to client)
- Maintain this buffering behavior; do not implement streaming to N8N webhook yet
- Log intermediate tokens/progress internally for monitoring (optional, for future streaming optimization)
- Ensure response is always complete before returning to API caller

**Backward Compatibility & Data Handling**
- Do not create migration for existing analyses; treat as legacy data
- Existing analyses: thinking_process=NULL, thinking_enabled=false, response_format='legacy'
- New analyses: populate all new columns appropriately
- Queries that filter by response_format must handle legacy null values gracefully
- All new fields optional in API response; client code receives only non-null values

**N8N Integration**
- N8N workflow sends same AnalysisRequest format unchanged
- N8N receives AnalysisSuccessResponse with new optional fields (thinking_process, response_format, operations_found)
- N8N workflow should check operations_found flag before processing trading_operations field
- Notification service receives operations_found flag to decide whether to include trading operations in notifications
- Health monitoring tracks thinking budget usage and cost metrics via logging

## Visual Design

No visual mockups provided for this backend-focused service improvement.

## Existing Code to Leverage

**Provider Factory Pattern (services/ai-analyzer/src/llm/provider.py)**
- Current implementation uses `get_llm_provider()` function with hardcoded model selection
- Refactor this function to accept model_name parameter and route to correct provider based on name
- Extend LLMProvider abstract class with new optional methods: `supports_thinking()`, `get_thinking_budget()`
- Keep existing AnthropicProvider and GroqProvider classes; enhance with thinking support
- Reuse error handling patterns (ConfigurationError, LLMError) for model validation

**Analysis Service Orchestration (services/ai-analyzer/src/services/analysis_service.py)**
- Current service coordinates LLM analysis, fallback extraction, and database persistence
- Extend analyze() method to accept optional thinking configuration from request or env vars
- Add new parsing step for markdown operations extraction before database storage
- Maintain existing fallback extraction logic for LLM failures
- Reuse confidence scoring for trading signals extracted from markdown

**Database Repository Pattern (services/ai-analyzer/src/db/analyses_repository.py)**
- Current create_analysis() method stores summary, trading_signals, ai_provider
- Extend to accept optional thinking_process, thinking_enabled, thinking_budget_tokens, response_format
- Add new parameter operations (JSONB) for trading operations storage
- Maintain referential integrity and timestamps
- Reuse connection pooling and parameterized queries

**Pydantic Models (services/ai-analyzer/src/models.py)**
- Current AnalysisSuccessResponse has: report_id, api_provider, summary, trading_signals, market_insights, symbols_mentioned, price_targets
- Add optional fields: thinking_process (str), response_format (str), operations_found (bool), trading_operations (List[dict])
- Create new TradingOperation model with flexible field validation (most fields optional)
- Extend AnalysisRequest to accept optional thinking_config parameter

**Error Handling Framework (services/ai-analyzer/src/utils/exceptions.py)**
- Current custom exceptions: ConfigurationError, LLMError, AnalysisError, InvalidResponseError
- Add new ConfigurationError context for unsupported models and missing provider keys
- Add InvalidResponseError context for markdown parsing failures (non-fatal)
- Maintain existing error handling strategy: log, gracefully degrade, return valid response

## Out of Scope

- Implementing streaming responses to N8N webhook (future optimization)
- Real-time cost monitoring dashboard (future feature)
- Auto-tuning thinking budgets based on report complexity (future enhancement)
- Caching of thinking processes across similar reports (future optimization)
- Batch processing multiple reports with shared thinking context (future feature)
- Custom prompt templates per trading portal (keep unified prompt)
- Support for multiple simultaneous thinking processes per request (single thinking process only)
- Integration with other LLM providers beyond Anthropic, Groq, Gemini (future evaluation)
