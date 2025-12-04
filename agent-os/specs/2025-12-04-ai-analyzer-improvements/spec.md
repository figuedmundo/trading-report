# Specification: AI Analyzer Service Improvements

## Executive Summary

This specification outlines comprehensive enhancements to the AI Analyzer Service that enable multi-provider LLM support (Anthropic Claude, Groq, and Google Gemini), extended thinking capabilities for deeper analysis, and flexible trading operations extraction. These improvements provide enterprise-grade configurability while maintaining backward compatibility with existing data. The service will shift to a single `LLM_MODEL` environment variable with automatic provider detection via model name prefix, enabling seamless switching between providers without code changes. Extended thinking, when enabled, will store reasoning traces for audit trails and improved debugging. Trading operations will be captured as flexible JSONB structures allowing evolving schema without database migrations.

## Problem Statement

The current AI Analyzer Service has several limitations:

1. **Single Provider Hardcoding**: Model names are hardcoded in provider classes, preventing runtime model switching and limiting flexibility.
2. **Binary Provider Choice**: Environment variables force selection between Anthropic and Groq at startup; dynamic provider detection is unavailable.
3. **No Thinking Process**: The service cannot leverage extended thinking capabilities available in newer LLM models, limiting analysis depth and quality.
4. **Rigid Response Format**: JSON-only structured responses make it difficult to capture nuanced reasoning and make the service inflexible to new fields without breaking changes.
5. **Schema Brittleness**: Database constraints on trading signals and response fields force migrations when new operation types or fields are needed.
6. **Limited Observability**: No visibility into LLM reasoning, thinking process duration, or partial analysis steps for debugging and improvement.
7. **Inconsistent Error Handling**: Different error handling patterns across providers and unclear degradation strategies.

## Goals and Objectives

1. **Multi-Provider Support**: Enable seamless switching between Anthropic Claude, Groq, and Google Gemini via `LLM_MODEL` environment variable with automatic provider detection.
2. **Extended Thinking Capability**: Add configurable extended thinking with token budget control (default 5000 tokens) to improve analysis quality and traceability.
3. **Flexible Response Parsing**: Parse LLM responses with markdown section markers (e.g., `## Trading Operations`) for free-form text + structured data extraction.
4. **JSONB Storage**: Store trading operations as flexible JSONB arrays without type constraints, allowing schema evolution without migrations.
5. **Sparse Trading Operations**: Support optional trading operations extraction with `operations_found` flag; empty/null operations only included when explicitly found.
6. **Backward Compatibility**: Maintain compatibility with existing analyses data; treat legacy data as read-only without requiring migrations.
7. **Improved Observability**: Log thinking tokens, provider-specific metrics, and analysis depth for operational visibility.
8. **Graceful Degradation**: Implement provider-agnostic fallback extraction without performance penalties when thinking fails.

## Specific Requirements

### Requirement 1: LLM Provider Factory with Auto-Detection

- Implement factory pattern with provider detection based on model name prefix
  - `claude*` model names → Anthropic provider
  - `mixtral*` or `llama*` → Groq provider
  - `gemini*` → Google provider (new)
  - Unknown prefix → raise ConfigurationError with clear guidance
- Accept single `LLM_MODEL` environment variable (e.g., `claude-3-5-sonnet-20241022`)
- Detect API key availability using `get_provider_from_model()` helper function
- Support multiple API keys in `.env` simultaneously (only detected provider key used)
- Log provider detection decision and model name during service initialization
- Raise ConfigurationError if API key missing for detected provider
- Update `.env.example` to show all provider keys as optional with clear documentation

### Requirement 2: Extended Thinking Configuration and Storage

- Add `THINKING_BUDGET_TOKENS` environment variable (default: 5000, range: 1000-32000)
- Implement thinking process at LLM layer, not in provider-specific code
- Create database migration to add `thinking_budget_tokens`, `thinking_tokens_used`, and `thinking_content` columns to analyses table
- Store thinking content as TEXT column for full reasoning trace and debugging
- Thinking enabled for all requests by default; disabled only if explicitly set to 0 or unavailable in provider
- Log thinking tokens consumed and remaining budget in response metadata
- Gracefully skip thinking if provider doesn't support it (no error thrown)
- Track cumulative thinking tokens per analysis for cost analysis

### Requirement 3: Response Format with Markdown Sections

- Design prompt template to return structured markdown with clear sections:
  - `## Summary` - Executive summary (150-250 words)
  - `## Market Analysis` - Market observations and trends
  - `## Trading Operations` - JSON array of operations (if found)
  - `## Risk Assessment` - Risk factors and mitigations
  - `## Additional Insights` - Extra observations
- Implement markdown parser in analysis service using regex for section extraction
- Extract sections case-insensitively using `##\s*(?P<section_name>[\w\s]+)` pattern
- Support "Trading Operations" and "Trading Signals" interchangeably in section headers
- Return free-form text for non-structured sections (no forced JSON parsing)
- Parse JSON array from Trading Operations section only if present and valid
- Fall back to empty array if JSON parsing fails (log warning, don't error)
- Ensure response always includes summary field regardless of section completeness

### Requirement 4: Trading Operations JSONB Structure and Flexibility

- Store trading operations as JSONB array with no type constraints in database
- Remove CHECK constraint on ai_provider from analyses table (allow future providers)
- Expand ai_provider to support "google", "fallback", "hybrid", and future types
- Trading operation structure: `{ action, symbol, entry_price, target_price, stop_loss, timeframe, confidence_score, [other_fields...] }`
- Allow undefined fields beyond core schema without validation errors
- Support operations_found boolean flag indicating whether operations were actually extracted
- Include operations_found in response only when explicitly returned by LLM
- Add index on analyses.trading_operations JSONB column for efficient queries
- Document JSONB structure in code comments for implementers
- Validate operations array is valid JSON before storage (catch and log parse errors)

### Requirement 5: Sparse Trading Operations Handling

- Add `operations_found` boolean field to database and response models
- Only include trading_operations in response when operations_found=true
- Default operations_found to false; set true only if LLM explicitly indicates operations exist
- Support null trading operations without error (treated as empty array for backward compat)
- Log when operations are skipped due to operations_found=false
- Update LLM prompt to include instruction: "Set operations_found=true only if you identified actual trading operations"
- Parse operations_found from markdown section or included in JSON metadata

### Requirement 6: Provider-Specific Implementation

**Anthropic Provider**:
- Model: claude-3-5-sonnet-20241022 (configurable via LLM_MODEL)
- Use `extended_thinking` parameter with budget from THINKING_BUDGET_TOKENS
- Return thinking content and input/output tokens in usage metrics
- Stream support: optional future enhancement (not in this spec)

**Groq Provider**:
- Model: mixtral-8x7b-32768 (configurable via LLM_MODEL)
- Note: Extended thinking not available; gracefully skip with INFO log
- Cache usage metrics for cost analysis
- Implement faster inference without thinking overhead

**Google Gemini Provider** (new):
- Model: gemini-2.0-flash (configurable via LLM_MODEL)
- Use google-generativeai SDK (add to requirements.txt)
- Support thinking mode with `google.generativeai.types.ThinkingConfig`
- Handle streaming responses by buffering complete response before return

### Requirement 7: Database Migration

- Migration file: `014_ai_analyzer_improvements.sql` in database/migrations/
- Add columns to analyses table:
  - `thinking_budget_tokens` (INTEGER, default: 5000)
  - `thinking_tokens_used` (INTEGER, nullable)
  - `thinking_content` (TEXT, nullable)
  - `operations_found` (BOOLEAN, default: false)
- Expand ai_provider VARCHAR(50) to support new providers without constraint errors
- Create indexes:
  - `idx_analyses_operations_found` on operations_found for queries
  - `idx_analyses_thinking_tokens` on thinking_tokens_used for cost analysis
  - `idx_analyses_ai_provider` on ai_provider for provider-specific queries
- Backfill existing records:
  - Set thinking_budget_tokens = 5000 for all existing
  - Set thinking_tokens_used = NULL for all existing
  - Set operations_found = true for all existing (preserve semantics: old data had operations)

### Requirement 8: Configuration Management

- Update `.env.example` with new variables:
  - `LLM_MODEL` - single model specifier (e.g., claude-3-5-sonnet-20241022)
  - `THINKING_BUDGET_TOKENS` - token budget for extended thinking (default: 5000)
  - Keep existing `ANTHROPIC_API_KEY`, `GROQ_API_KEY` for backward compat
  - Add `GOOGLE_API_KEY` for Gemini support
  - Document that only detected provider's key is required
- Update config.py to parse thinking budget with type validation
- Support model name from environment or config file
- Log which provider was detected based on model name during startup

### Requirement 9: Error Handling and Resilience

- Implement provider-agnostic error handling at analyzer layer (not provider-specific)
- Handle LLM errors with exponential backoff (max 3 retries with 2s base)
- Gracefully degrade to fallback extraction on:
  - API key missing → warning log, use fallback (no throw)
  - Timeout (30s) → warning log, use fallback (no throw)
  - Invalid response format → warning log, use fallback (no throw)
  - JSON parsing failure → warning log, continue with partial data (no throw)
  - Provider unavailable → switch to fallback, log error
- Log error context: report_id, provider, error_code, model_name, thinking_tokens_used
- Never expose raw API errors to HTTP response (sanitize)
- Return 500 only for unrecoverable fatal errors (no LLM + fallback failed)

### Requirement 10: Observability and Metrics

- Log metadata for every analysis:
  - provider_detected (e.g., "anthropic")
  - model_name (e.g., "claude-3-5-sonnet-20241022")
  - thinking_tokens_used (if applicable)
  - thinking_tokens_budget (configuration value)
  - total_input_tokens (LLM usage)
  - total_output_tokens (LLM usage)
  - response_latency_ms
  - provider_response_time_ms (isolated)
  - fallback_used (boolean)
  - operations_found (boolean)
- Store metrics in database for cost tracking and performance analysis
- Add columns to analyses table for token tracking if needed
- Log ratios: thinking_tokens_used / thinking_tokens_budget for efficiency analysis
- Implement health check endpoint that includes provider availability status

## Visual Design

No UI components in this specification (backend service only).

## Existing Code to Leverage

**services/ai-analyzer/src/llm/provider.py**
- Existing abstract LLMProvider base class with analyze() and get_provider_name()
- AnthropicProvider and GroqProvider implementations already follow factory pattern
- Extend to add GoogleProvider class following same pattern
- Reuse error handling patterns and logging structure
- Keep provider.py focused on provider instantiation and API calls

**services/ai-analyzer/src/services/analysis_service.py**
- Existing orchestration layer with LLMAnalyzer, FallbackExtractor, ConfidenceScorer integration
- Already implements graceful fallback when LLM fails (line 65-70)
- Confidence scorer can be extended to handle thinking tokens metadata
- Keep orchestration pattern; add thinking and operations parsing as new responsibilities

**services/ai-analyzer/src/llm/analyzer.py**
- Existing timeout handling (30 seconds) with asyncio.wait_for
- Already catches InvalidResponseError and returns None for fallback
- Extend to handle thinking-specific errors and metrics logging
- Keep error handling structure (try-except patterns are good)

**services/ai-analyzer/src/db/analyses_repository.py**
- Database abstraction layer for storing analyses
- Already stores trading_signals JSONB; pattern works for operations_found
- Extend create_analysis() signature to accept thinking metadata
- Reuse parameterized queries and connection pooling patterns

**services/ai-analyzer/src/models.py**
- Pydantic models for request/response validation
- AnalysisSuccessResponse already has api_provider, summary, trading_signals fields
- Add thinking_content, thinking_tokens_used, operations_found to response models
- TradingSignal model can remain unchanged (flexible JSONB in DB is separate)
- Reuse field_validator patterns for optional field validation

**services/ai-analyzer/src/extraction/fallback.py**
- Existing keyword-based extraction as fallback
- No changes needed; works as-is for degradation
- Can be enhanced later to also extract operations if needed

**services/ai-analyzer/src/utils/exceptions.py**
- Existing ConfigurationError, AnalysisError, LLMError hierarchy
- Add ThinkingError as subclass of LLMError if thinking-specific handling needed
- Reuse exception patterns throughout

**database/migrations/006_create_analyses_table.sql**
- Current analyses table schema with JSONB trading_signals
- Migration 006 shows pattern for JSONB columns and indexing
- Create new migration following same structure and patterns
- Reference this migration for constraint definition and index creation

**agent-os/standards/backend/models.md**
- Timestamps, data integrity, appropriate types guidance applies
- Ensure all new columns have defaults and NOT NULL constraints
- Use proper timezone handling (TIMESTAMPTZ)

## Architecture & Design Patterns

### Provider Factory Pattern

The service will implement a provider factory with model-based detection:

```
LLM_MODEL env var (e.g., "claude-3-5-sonnet-20241022")
    ↓
get_provider_from_model() function
    ↓
Extract model prefix: "claude" | "mixtral" | "gemini" etc.
    ↓
Load corresponding API key
    ↓
Instantiate provider (AnthropicProvider | GroqProvider | GoogleProvider)
    ↓
Pass to LLMAnalyzer
```

### Extended Thinking Flow

```
AnalysisRequest
    ↓
LLMAnalyzer.analyze()
    ↓
Provider.analyze() with thinking_budget_tokens
    ↓
LLM returns:
  - thinking (if enabled)
  - response text with markdown sections
  - usage metrics
    ↓
AnalysisService parses markdown sections
    ↓
Extract Trading Operations from section
    ↓
Store in DB:
  - thinking_content (TEXT)
  - thinking_tokens_used (INTEGER)
  - operations_found (BOOLEAN)
    ↓
AnalysisSuccessResponse with all metadata
```

### Markdown Response Parsing

```
Raw LLM response:
  ## Summary
  Executive summary text...

  ## Market Analysis
  Market observations...

  ## Trading Operations
  [
    { "action": "BUY", "symbol": "AAPL", ... }
  ]

  ## Risk Assessment
  Risk factors...

Parser extracts:
  summary: "Executive summary text..."
  market_insights: ["Market observations..."]
  trading_operations: [{ "action": "BUY", "symbol": "AAPL", ... }]
  operations_found: true
```

### Error Handling and Degradation

```
AnalysisRequest
    ↓
Try LLM analysis with thinking
    ↓
LLM succeeds? ✓ → Return response
  │
  ✗ (timeout, error, invalid response)
    ↓
Try fallback extraction
    ↓
Fallback succeeds? ✓ → Return fallback response (operations_found=false)
  │
  ✗ (both failed)
    ↓
Return error response with details
```

## Implementation Details

### File Organization

```
services/ai-analyzer/src/
├── llm/
│   ├── provider.py          # Updated: Add GoogleProvider, factory detection
│   ├── analyzer.py          # Updated: Thinking handling, markdown parsing
│   └── __init__.py
├── services/
│   └── analysis_service.py  # Updated: Orchestration for thinking/operations
├── api/
│   └── routes.py            # No changes (uses updated response models)
├── models.py                # Updated: Add thinking/operations_found fields
├── db/
│   ├── analyses_repository.py  # Updated: Persist thinking metadata
│   └── __init__.py
├── extraction/
│   ├── markdown_parser.py   # NEW: Parse markdown sections
│   ├── fallback.py          # No changes
│   └── __init__.py
└── utils/
    ├── exceptions.py        # Minor: Add new error types if needed
    └── logger.py
```

### Key Functions to Implement

**1. `get_provider_from_model()` in llm/provider.py**
```
Purpose: Detect provider based on model name prefix
Input: model_name string (e.g., "claude-3-5-sonnet-20241022")
Output: Tuple(provider_class, provider_name)
Logic:
  - Extract prefix before first hyphen/digit
  - Match against known patterns (claude, mixtral, gemini, etc.)
  - Check corresponding API key exists
  - Return provider class and name
  - Raise ConfigurationError if unknown or no API key
```

**2. `parse_markdown_sections()` in extraction/markdown_parser.py**
```
Purpose: Extract sections from markdown response
Input: markdown_text string
Output: Dict with section_name → content mappings
Logic:
  - Find all ## Section Name patterns
  - Extract content until next ## or EOF
  - Normalize section names (lowercase, trim)
  - Return dict: { "summary": "...", "trading_operations": "...", ... }
```

**3. `extract_trading_operations()` in extraction/markdown_parser.py**
```
Purpose: Parse JSON from Trading Operations markdown section
Input: markdown_section content string, raw_text context
Output: Tuple(operations_array, operations_found_boolean)
Logic:
  - Find JSON array in section (first [ to matching ])
  - Parse JSON safely (catch exceptions)
  - Validate each operation has required fields (action, symbol)
  - Return (operations, true) if valid; ([], false) if empty/invalid
  - Log parsing failures as warnings (don't throw)
```

**4. Enhanced `LLMAnalyzer.analyze()` in llm/analyzer.py**
```
Purpose: Coordinate provider analysis with thinking support
Changes:
  - Accept thinking_budget_tokens parameter
  - Pass to provider.analyze()
  - Capture thinking_tokens_used from response metadata
  - Parse markdown sections from response
  - Log thinking efficiency metrics
  - Return analysis dict with thinking metadata
```

**5. `AnalysisService.analyze()` updates in services/analysis_service.py**
```
Changes:
  - Call markdown_parser.parse_markdown_sections()
  - Call markdown_parser.extract_trading_operations()
  - Set operations_found boolean based on extraction result
  - Pass thinking metadata to database
  - Include all metadata in response
```

### Response Model Updates

```python
class AnalysisSuccessResponse(BaseModel):
    report_id: str
    api_provider: str
    summary: str
    trading_signals: List[TradingSignal] = []
    market_insights: List[str] = []
    symbols_mentioned: List[str] = []
    price_targets: Dict[str, Optional[float]] = {}
    raw_extracted_text: str

    # NEW FIELDS
    thinking_budget_tokens: Optional[int] = None
    thinking_tokens_used: Optional[int] = None
    thinking_content: Optional[str] = None
    operations_found: bool = False
    model_name: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
```

## Configuration

### Environment Variables

| Variable | Type | Default | Description | Example |
|----------|------|---------|-------------|---------|
| `LLM_MODEL` | string | (required) | Model identifier for provider detection | `claude-3-5-sonnet-20241022` |
| `THINKING_BUDGET_TOKENS` | int | 5000 | Token budget for extended thinking | `8000` |
| `ANTHROPIC_API_KEY` | string | (optional) | Anthropic API key | `sk-ant-...` |
| `GROQ_API_KEY` | string | (optional) | Groq API key | `gsk-...` |
| `GOOGLE_API_KEY` | string | (optional) | Google Gemini API key | (new) |

### Configuration Validation

- At startup, parse LLM_MODEL to detect provider
- Validate corresponding API key exists or raise ConfigurationError
- Validate THINKING_BUDGET_TOKENS in range [1000, 32000] or use default
- Log detected provider, model, and thinking budget

## Testing Strategy

### Unit Tests

1. **Provider Detection Tests** (`test_provider_detection.py`)
   - Test each model prefix → correct provider mapping
   - Test missing API key → raises ConfigurationError
   - Test unknown model prefix → raises ConfigurationError

2. **Markdown Parsing Tests** (`test_markdown_parser.py`)
   - Test extracting all section types
   - Test case-insensitive section matching
   - Test JSON parsing from Trading Operations section
   - Test malformed JSON → returns empty array with warning
   - Test missing section → returns empty content

3. **Trading Operations Tests** (`test_trading_operations.py`)
   - Test operations_found = true when ops present
   - Test operations_found = false when ops absent
   - Test sparse operations (null/empty arrays)
   - Test flexible JSONB fields

4. **Thinking Metadata Tests** (`test_thinking_metadata.py`)
   - Test thinking tokens captured from response
   - Test thinking disabled when budget = 0
   - Test thinking unavailable → graceful skip

### Integration Tests

1. **End-to-End Analysis** (`test_analysis_e2e.py`)
   - Test full request → response cycle
   - Test with thinking enabled
   - Test markdown parsing produces valid response
   - Test database persistence includes thinking metadata

2. **Provider Switching** (`test_provider_switching.py`)
   - Change LLM_MODEL, restart service, verify provider detected
   - Test each provider produces valid response format

3. **Fallback Tests** (`test_fallback_scenarios.py`)
   - Test LLM timeout → fallback extraction
   - Test invalid LLM response → fallback extraction
   - Test missing API key → fallback extraction

### No New Tests During Implementation

Per project standards (`testing/test-writing.md`), do NOT write tests for every change or intermediate step. Focus on completing implementation first. Strategic tests should be added only at logical completion points, not during development.

## Performance Considerations

### Thinking Token Overhead

- Extended thinking adds latency proportional to thinking_budget_tokens
- Estimate: ~5s additional latency for 5000 thinking tokens (varies by provider)
- Budget can be reduced to 1000 tokens for faster responses with less depth
- Groq provider unaffected (no thinking support)
- Monitor thinking_tokens_used / thinking_tokens_budget ratio for efficiency

### Response Parsing Overhead

- Markdown parsing adds <100ms latency per response (regex-based)
- JSON extraction from markdown ~50ms
- Negligible compared to LLM latency (typically 5-30 seconds)

### Database Storage

- JSONB thinking_content storage: ~2-5KB per record (variable)
- Indexes on operations_found, thinking_tokens_used enable efficient queries
- INDEX on analyses.thinking_tokens_used supports cost analysis queries
- Historical cleanup: implement retention policy if needed (out of scope)

### Optimization Tips

1. Set THINKING_BUDGET_TOKENS=1000 in production if speed critical, quality acceptable
2. Use Groq provider for speed-focused workloads (no thinking overhead)
3. Implement connection pooling for database (already in place)
4. Cache provider instantiation (already done in get_llm_provider())

## Migration & Rollout

### Database Migration Strategy

1. **No Live Schema Changes Required**: Analysis table schema can be modified while service is running
   - Add nullable columns first (thinking_content, thinking_tokens_used, operations_found)
   - Add non-nullable columns with defaults (thinking_budget_tokens)
   - No data reshaping needed

2. **Migration Execution**:
   - Run 014_ai_analyzer_improvements.sql
   - Backfill existing records with defaults (5000 tokens, null thinking, operations_found=true)
   - Create indexes (non-blocking in PostgreSQL 11+)
   - Service can process new requests during migration

3. **Backward Compatibility**:
   - Existing analysis records untouched (no migration of old data)
   - Old records treated as legacy: operations_found=true, thinking_tokens_used=NULL
   - API response includes all new fields for consistency
   - No client code changes required

4. **Rollback Plan**:
   - Drop new columns if needed (reverses migration)
   - Service continues working with old schema (using NULL for new fields)
   - No data loss

### Deployment Steps

1. Deploy code changes with feature flags disabled (if possible) or LLM_MODEL set to existing model
2. Run database migration (014_ai_analyzer_improvements.sql)
3. Update .env with LLM_MODEL and THINKING_BUDGET_TOKENS
4. Restart AI Analyzer service
5. Verify provider detection in logs
6. Monitor error rates and thinking token usage

### Canary Testing

1. Set THINKING_BUDGET_TOKENS=1000 initially (minimal thinking)
2. Run against sample reports
3. Verify markdown parsing extracts sections correctly
4. Check trading_operations_found logic
5. Gradually increase THINKING_BUDGET_TOKENS if quality improves
6. Switch providers (change LLM_MODEL) and test each

## Out of Scope

- Streaming response support (buffer and return complete analysis)
- Token usage billing integration (only logging for now)
- Custom provider implementations beyond Anthropic, Groq, Google
- Real-time provider failover (manual LLM_MODEL change required)
- Thinking process visualization in UI (backend storage only)
- Training on thinking content (storage only)
- Historical thinking analysis and trending
- Rate limiting per provider (use N8N or external service)
- Caching of LLM responses
- Batch analysis processing
- Async thinking (e.g., queue-based delayed thinking)
- Multi-step reasoning with intermediate storage
- Provider-specific prompt tuning beyond basic structure
- Cost tracking and alerts per provider

## Appendix: Code Examples

### Example 1: Provider Detection

```python
# services/ai-analyzer/src/llm/provider.py

def get_provider_from_model(model_name: str) -> Tuple[Type[LLMProvider], str]:
    """
    Detect LLM provider from model name prefix.

    Args:
        model_name: Model identifier (e.g., "claude-3-5-sonnet-20241022")

    Returns:
        Tuple of (ProviderClass, provider_name)

    Raises:
        ConfigurationError: If provider not detected or API key missing
    """
    if not model_name:
        raise ConfigurationError("LLM_MODEL environment variable not set")

    # Extract prefix (before first digit or hyphen)
    prefix = model_name.split('-')[0].lower()

    provider_map = {
        'claude': ('AnthropicProvider', 'ANTHROPIC_API_KEY'),
        'mixtral': ('GroqProvider', 'GROQ_API_KEY'),
        'llama': ('GroqProvider', 'GROQ_API_KEY'),
        'gemini': ('GoogleProvider', 'GOOGLE_API_KEY'),
    }

    if prefix not in provider_map:
        raise ConfigurationError(
            f"Unknown model prefix: {prefix}. "
            f"Supported: {', '.join(provider_map.keys())}",
            context={"model_name": model_name, "prefix": prefix}
        )

    provider_class_name, api_key_var = provider_map[prefix]
    api_key = os.getenv(api_key_var)

    if not api_key:
        raise ConfigurationError(
            f"API key {api_key_var} required for {prefix} models",
            context={"model_name": model_name, "provider": prefix}
        )

    # Import and return provider class
    provider_class = globals()[provider_class_name]
    logger.info(f"Detected provider: {prefix} for model: {model_name}")
    return provider_class, prefix
```

### Example 2: Markdown Section Parsing

```python
# services/ai-analyzer/src/extraction/markdown_parser.py

import re
import json
from typing import Dict, Tuple, List, Optional

def parse_markdown_sections(response_text: str) -> Dict[str, str]:
    """
    Extract markdown sections from LLM response.

    Sections marked with ##, e.g.:
    ## Summary
    text...
    ## Trading Operations
    [...JSON...]

    Args:
        response_text: Raw LLM response with markdown sections

    Returns:
        Dict mapping section names (lowercase) to content
    """
    sections = {}

    # Find all ## Section Name patterns
    pattern = r'##\s*(?P<section_name>[\w\s]+?)\s*\n(?P<content>.*?)(?=##|$)'

    for match in re.finditer(pattern, response_text, re.DOTALL | re.IGNORECASE):
        section_name = match.group('section_name').strip().lower()
        content = match.group('content').strip()
        sections[section_name] = content

    return sections

def extract_trading_operations(
    section_content: str,
    context_text: str
) -> Tuple[List[Dict], bool]:
    """
    Extract trading operations from markdown section.

    Looks for JSON array in section content. Sets operations_found=True
    only if valid operations array is found with at least one operation.

    Args:
        section_content: Content from Trading Operations section
        context_text: Full raw text (for confidence scoring if needed)

    Returns:
        Tuple of (operations_list, operations_found_boolean)
    """
    operations = []
    operations_found = False

    if not section_content or not section_content.strip():
        return operations, operations_found

    # Find JSON array in content
    json_match = re.search(r'\[.*?\]', section_content, re.DOTALL)

    if not json_match:
        logger.warning("No JSON array found in Trading Operations section")
        return operations, operations_found

    try:
        json_str = json_match.group(0)
        operations = json.loads(json_str)

        # Validate operations is list
        if not isinstance(operations, list):
            logger.warning("Trading Operations JSON is not an array")
            return [], False

        # Mark as found only if list has elements with required fields
        for op in operations:
            if isinstance(op, dict) and 'action' in op and 'symbol' in op:
                operations_found = True
                break

        if operations_found:
            logger.info(f"Found {len(operations)} trading operations")
        else:
            logger.info("No valid trading operations with required fields found")

        return operations, operations_found

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse Trading Operations JSON: {str(e)}")
        return [], False
    except Exception as e:
        logger.warning(f"Error extracting trading operations: {str(e)}")
        return [], False
```

### Example 3: Anthropic Provider with Thinking

```python
# services/ai-analyzer/src/llm/provider.py (partial)

class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider with extended thinking support."""

    def __init__(self, api_key: str, thinking_budget_tokens: int = 5000):
        """Initialize Anthropic provider."""
        self.api_key = api_key
        self.thinking_budget_tokens = thinking_budget_tokens
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ConfigurationError(
                "anthropic library not installed. Install with: pip install anthropic",
                context={"provider": "anthropic"}
            )

    async def analyze(self, content: str) -> Dict[str, Any]:
        """
        Analyze content using Claude with extended thinking.

        Returns Dict with:
        - thinking: thinking content (if enabled)
        - thinking_tokens_used: tokens consumed by thinking
        - response: analysis text with markdown sections
        - input_tokens: usage.input_tokens
        - output_tokens: usage.output_tokens
        """
        prompt = f"""Analyze the following trading report and provide:

## Summary
Executive summary (150-250 words) of key findings and recommendations.

## Market Analysis
Market observations, trends, and economic factors mentioned.

## Trading Operations
If you identified specific trading operations (BUY/SELL/HOLD signals),
provide as JSON array with objects containing: action, symbol, entry_price,
target_price, stop_loss, timeframe, confidence_score.
Only include if you found actual trading signals. Set operations_found=true if present.

## Risk Assessment
Risk factors, market risks, and mitigation strategies.

## Additional Insights
Any other relevant observations.

REPORT CONTENT:
{content}

Return ONLY the analysis with markdown sections, no preamble."""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Should come from config
                max_tokens=2000,
                temperature=0,
                thinking={
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget_tokens
                } if self.thinking_budget_tokens > 0 else None,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract response content and thinking
            analysis_text = ""
            thinking_content = None

            for block in response.content:
                if block.type == "text":
                    analysis_text = block.text
                elif block.type == "thinking":
                    thinking_content = block.thinking

            return {
                "response": analysis_text,
                "thinking": thinking_content,
                "thinking_tokens_used": response.usage.cache_creation_input_tokens
                    if hasattr(response.usage, 'cache_creation_input_tokens') else None,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "api_provider": "anthropic"
            }

        except Exception as e:
            raise LLMError(
                f"Anthropic API call failed: {str(e)}",
                context={"original_error": str(e)}
            )
```

### Example 4: Database Migration

```sql
-- database/migrations/014_ai_analyzer_improvements.sql
-- Add extended thinking, operations_found, and flexible provider support

BEGIN;

-- Add new columns for thinking support
ALTER TABLE analyses
ADD COLUMN thinking_budget_tokens INTEGER DEFAULT 5000 NOT NULL,
ADD COLUMN thinking_tokens_used INTEGER,
ADD COLUMN thinking_content TEXT;

-- Add operations_found flag
ALTER TABLE analyses
ADD COLUMN operations_found BOOLEAN DEFAULT false NOT NULL;

-- Backfill existing records
UPDATE analyses
SET
  thinking_budget_tokens = 5000,
  thinking_tokens_used = NULL,
  thinking_content = NULL,
  operations_found = true
WHERE operations_found IS NULL;

-- Expand ai_provider VARCHAR to support new providers
-- First drop check constraint if exists
ALTER TABLE analyses
DROP CONSTRAINT IF EXISTS valid_provider;

-- Extend column size and add comment for flexibility
ALTER TABLE analyses
ALTER COLUMN ai_provider TYPE VARCHAR(100);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_analyses_operations_found
ON analyses(operations_found)
WHERE operations_found = true;

CREATE INDEX IF NOT EXISTS idx_analyses_thinking_tokens
ON analyses(thinking_tokens_used DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_analyses_ai_provider
ON analyses(ai_provider);

-- Index JSONB operations for future queries
CREATE INDEX IF NOT EXISTS idx_analyses_operations_jsonb
ON analyses USING GIN(trading_signals);

COMMIT;
```

### Example 5: Configuration Loading

```python
# services/ai-analyzer/src/config.py

import os
from dataclasses import dataclass

@dataclass
class Config:
    """Service configuration loaded from environment."""

    llm_model: str
    thinking_budget_tokens: int
    analysis_timeout: int = 30
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        llm_model = os.getenv("LLM_MODEL")
        if not llm_model:
            raise ConfigurationError(
                "LLM_MODEL environment variable not set. "
                "Example: claude-3-5-sonnet-20241022"
            )

        thinking_budget_tokens = int(os.getenv("THINKING_BUDGET_TOKENS", "5000"))

        # Validate thinking budget range
        if not (1000 <= thinking_budget_tokens <= 32000):
            raise ConfigurationError(
                f"THINKING_BUDGET_TOKENS must be between 1000 and 32000, "
                f"got {thinking_budget_tokens}"
            )

        logger.info(
            "Configuration loaded",
            extra={
                "llm_model": llm_model,
                "thinking_budget_tokens": thinking_budget_tokens,
            }
        )

        return cls(
            llm_model=llm_model,
            thinking_budget_tokens=thinking_budget_tokens,
        )
```

### Example 6: Updated Analysis Request/Response

```python
# services/ai-analyzer/src/models.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class AnalysisRequest(BaseModel):
    """Request body for POST /api/v1/analyze endpoint."""
    report_id: str
    raw_extracted_text: str

class AnalysisSuccessResponse(BaseModel):
    """Success response body for analysis endpoint."""
    report_id: str
    api_provider: str
    summary: str
    trading_signals: List[Dict] = Field(default_factory=list)
    market_insights: List[str] = Field(default_factory=list)
    symbols_mentioned: List[str] = Field(default_factory=list)
    price_targets: Dict[str, Optional[float]] = Field(default_factory=dict)
    raw_extracted_text: str

    # Extended thinking metadata
    thinking_budget_tokens: Optional[int] = None
    thinking_tokens_used: Optional[int] = None
    thinking_content: Optional[str] = None

    # Trading operations flexibility
    operations_found: bool = False

    # Provider and performance metadata
    model_name: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    response_latency_ms: Optional[int] = None
```

## Summary

This specification provides a comprehensive roadmap for modernizing the AI Analyzer Service with multi-provider support, extended thinking capabilities, and flexible response parsing. The design prioritizes:

- **Flexibility**: Single LLM_MODEL variable with auto-detection enables seamless provider switching
- **Observability**: Comprehensive logging of thinking tokens, provider metrics, and performance data
- **Resilience**: Graceful degradation with fallback extraction prevents service failures
- **Compatibility**: No schema migrations required; legacy data remains valid
- **Extensibility**: JSONB storage of trading operations allows schema evolution without database changes

The implementation follows established patterns in the codebase (factory pattern, graceful degradation, structured logging) and maintains alignment with project coding standards (error handling, validation, async operations).

Key milestones for implementation:
1. Provider factory pattern and model detection
2. Markdown response parsing infrastructure
3. Extended thinking integration (provider-specific)
4. Database migration and backward compatibility
5. Comprehensive testing and production validation

---

**Document Version**: 1.0
**Last Updated**: December 4, 2025
**Status**: Ready for Implementation
