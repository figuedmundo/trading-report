# AI Analysis Engine - Key Design Decisions

## Summary of Design Choices

This document captures the critical architectural and functional decisions made during requirements gathering for the AI Analysis Engine feature.

---

## 1. AI Provider Architecture

**Decision:** Flexible multi-provider support with fallback logic
- Primary: ANTHROPIC_API_KEY (Claude models)
- Fallback: GROQ_API_KEY (Groq API)
- Configuration: Environment variables only (no hardcoding)

**Rationale:** Provides cost optimization and resilience. Users can choose their preferred provider or switch on failures.

---

## 2. Summary Format

**Decision:** Fixed format output with 200-300 word executive summary
- Summary text (natural language overview)
- Trading signals (structured array)
- Market insights (key observations)
- Symbols/tickers mentioned
- Price targets identified
- Confidence scores for each signal

**Rationale:** Consistent, actionable output that balances human-readability with structured data for automation.

---

## 3. Trading Signal Structure

**Decision:** Minimal but complete signal model
```
{
  "action": "BUY|SELL|HOLD",
  "symbol": "AAPL",
  "entry_price": 150.00,
  "target_price": 165.00,
  "stop_loss": 145.00,
  "timeframe": "short-term",
  "confidence_score": 0.9
}
```

**Rationale:** Covers essential trading decision factors while remaining simple to implement and use. Timeframe helps traders assess position duration.

---

## 4. Confidence Scoring Model

**Decision:** Simple 3-tier confidence approach (signal-focused, not analyst-based)
- 0.9: Explicit mention in report (clear recommendation)
- 0.6: Implied/inferred from content
- 0.3: Passing mention or low conviction

**Rationale:**
- Simple to implement (no complex ML models)
- Focused on signal quality vs analyst credibility
- Sufficient granularity for filtering/sorting signals
- Aligns with "minimal implementation" philosophy

---

## 5. Failure Handling Strategy

**Decision:** Two-tier approach
- **LLM Failure:** Do NOT store failed analyses; proceed to fallback
- **Fallback:** Keyword-matching extraction if LLM unavailable
- **Result:** Always attempt to extract signals, even if LLM fails

**Rationale:**
- Prevents database pollution with error records
- Ensures value even when LLM APIs are unavailable
- Simple fallback is better than no analysis
- Maintains uptime during API outages

---

## 6. Database Design Philosophy

**Decision:** Minimal schema approach
- Single `analyses` table with essential fields only
- No tracking of analysis failures
- Simple relationships (foreign key to reports)

**Fields:**
- `id`: Primary key (UUID or serial)
- `report_id`: Foreign key to reports table
- `summary`: Text (executive summary)
- `trading_signals`: JSON array (structured signals)
- `api_provider`: String (which API was used)
- `created_at`: Timestamp

**Rationale:**
- Reduces schema complexity
- Faster queries
- Easy to migrate if needs evolve
- Sufficient for MVP inbox functionality

---

## 7. Data Separation Pattern

**Decision:** Keep raw_extracted_text separate from analysis
- Report extraction output: `reports.raw_extracted_text`
- Analysis output: `analyses.summary` + `analyses.trading_signals`
- API responses: Include both, but distinct fields

**Rationale:**
- Maintains audit trail (raw content unchanged)
- Allows re-analysis without re-scraping
- Clear separation of concerns
- Supports future analysis method comparisons

---

## 8. Error Handling Pattern

**Decision:** Graceful degradation with logging
- LLM API calls wrapped in try-catch
- Timeout handling (configurable)
- Rate limit detection
- Invalid response handling
- Fallback to keyword extraction on any failure
- Structured logging with report context

**Rationale:**
- Maintains service resilience
- Provides debugging information
- Clear visibility into failure modes

---

## 9. Scope Boundaries - Explicit Exclusions

**Out of Scope (Phase 1):**
- Trend analysis across multiple reports
- Portfolio aggregation and risk assessment
- Multi-report correlation analysis
- Analyst credibility tracking
- Performance backtesting
- Real-time market data integration
- Advanced ML-based confidence scoring

**Rationale:** Focus on single-report analysis first. Multi-report analysis would require significant additional complexity and is better handled in later phases.

---

## 10. Code Reuse Strategy

**Decision:** Adopt patterns from existing services (playwright-scraper)
- Config class for configuration management
- Custom exception classes for errors
- FastAPI service structure
- Async/await patterns
- Pydantic models for validation
- Structured logging approach

**Rationale:**
- Consistency across codebase
- Reduces learning curve for developers
- Leverages proven patterns
- Easier testing and maintenance

---

## 11. Testing Scope

**Decision:** Minimal testing (1-2 tests max)
- Focus on core happy-path: extract signals from report
- Mock LLM API calls
- Skip exhaustive test coverage

**Rationale:**
- MVP focused on functionality over robustness
- Full test suite can be added in Phase 2
- Reduces initial implementation time

---

## 12. API Response Design

**Decision:** Structured response with transparency
```json
{
  "report_id": "uuid",
  "api_provider": "anthropic|groq",
  "summary": "200-300 word text...",
  "trading_signals": [
    {
      "action": "BUY",
      "symbol": "AAPL",
      "entry_price": 150.0,
      "target_price": 165.0,
      "stop_loss": 145.0,
      "timeframe": "short-term",
      "confidence_score": 0.9
    }
  ],
  "market_insights": ["insight1", "insight2"],
  "symbols_mentioned": ["AAPL", "MSFT"],
  "price_targets": {"AAPL": 165.0, "MSFT": 380.0},
  "raw_extracted_text": "original content"
}
```

**Rationale:**
- Includes provider info for transparency
- Separates concerns (summary vs signals vs raw text)
- Enables downstream filtering/prioritization
- Maintains raw content for audit trails

---

## Implementation Constraints & Considerations

### Performance Targets
- Analysis should complete within 5-10 seconds per report
- LLM API timeout: 30 seconds (fallback after)
- Database inserts should be batched if processing multiple reports

### Configuration Management
- All API keys from environment variables
- No hardcoded models or providers
- Configurable LLM model names per provider
- Configurable confidence thresholds for fallback

### Integration Points
- Receives: report_id + raw_extracted_text from content-extraction service
- Sends: analysis results to PostgreSQL analyses table
- Consumes: Anthropic Claude API or Groq API
- Called by: N8N workflow orchestration

### Monitoring & Observability
- Log every analysis attempt with report_id
- Track API provider usage
- Log fallback extraction triggers
- Monitor LLM API error rates
- Track analysis success/failure rates

---

## Next Steps for Implementation

1. **Specification Writing:** Use `/write-spec` to generate detailed technical spec
2. **Schema Migration:** Create database migration for analyses table
3. **Service Implementation:** Implement FastAPI service with:
   - LLM provider abstraction
   - Prompt engineering for signal extraction
   - Fallback keyword extraction logic
4. **Testing:** Write 1-2 core functionality tests
5. **N8N Integration:** Update workflow to call analysis service
6. **Documentation:** Update service API documentation

---

**Last Updated:** November 27, 2025
**Status:** Requirements Finalized - Ready for Specification Writing
