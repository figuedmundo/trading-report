# Spec Requirements: AI Analysis Engine

## Initial Description
Analyze extracted report content with LLM (Claude/Groq); generate trading signals and key insights; confidence scoring for recommendations; store analysis results in database.

## Requirements Discussion

### First Round Questions

**Q1:** Should I assume the AI provider selection defaults to checking ANTHROPIC_API_KEY in .env, with GROQ_API_KEY as a fallback option?
**Answer:** Yes, that's correct. Default in .env variables (ANTHROPIC_API_KEY or GROQ_API_KEY with fallback).

**Q2:** I'm thinking the summary should be a 200-300 word executive summary. Should it include: summary text, trading signals (action/price targets), market insights, symbols mentioned, price targets, and confidence scores all in one response?
**Answer:** Yes, exactly. 200-300 word executive summary with: summary text, trading signals, market insights, symbols, price targets, confidence scores.

**Q3:** For trading signals, should the structure include: action (BUY/SELL/HOLD), symbol, entry/target prices, stop-loss, timeframe, and a confidence score (0.0-1.0)?
**Answer:** Yes. Trading signal structure: action (BUY/SELL/HOLD), symbol, entry/target prices, stop-loss, timeframe, confidence score.

**Q4:** For confidence scoring, should I use a simple approach where 0.9 = explicit mention, 0.6 = implied/inferred, 0.3 = passing mention? And should this be signal-focused rather than analyst credibility-based?
**Answer:** Yes. Use simple approach (0.9=explicit, 0.6=implied, 0.3=passing mention). Keep signal-focused, NOT analyst credibility-based.

**Q5:** If the LLM analysis fails (timeout, API error, invalid response), what should we do? Store the failure as an "error" analysis, or skip storing it? And should we have a fallback keyword-matching extraction if LLM fails?
**Answer:** DON'T store failed analyses. YES to fallback keyword-matching extraction if LLM fails.

**Q6:** For database design, should I create a minimal schema with just an `analyses` table containing: id, report_id, summary, trading_signals (JSON), api_provider, created_at? Or do you need additional fields for tracking analysis state or lineage?
**Answer:** Minimal schema - ONLY what's needed for inbox. Suggested minimal table: analyses(id, report_id, summary, trading_signals JSON, api_provider, created_at).

**Q7:** Should the API response keep raw_extracted_text separate from the analysis results, or should it be filtered out in the response?
**Answer:** Keep raw_extracted_text separate.

**Q8:** What should be out of scope for this feature? Should we exclude trend analysis across multiple reports, portfolio aggregation, risk assessment across positions, or other capabilities?
**Answer:** Exclude everything NOT directly related to report analysis (e.g., trend analysis across multiple reports, portfolio aggregation).

### Existing Code to Reference

**Similar Features Identified:**
- Feature: Playwright Scraper Service - Path: `services/playwright-scraper/`
  - Components to potentially reuse: Config class pattern, custom exceptions, FastAPI structure
  - Backend logic to reference: Service initialization, error handling patterns, async operations

### Follow-up Questions

No follow-up questions were necessary. User provided clear, actionable answers to all clarifications.

## Visual Assets

### Files Provided:
No visual assets provided.

### Visual Insights:
N/A - No mockups, wireframes, or design references were included.

## Requirements Summary

### Functional Requirements

**AI Analysis Processing:**
- Accept extracted report content (raw_extracted_text) as input
- Analyze content using configurable LLM provider (Anthropic Claude or Groq)
- Generate executive summary (200-300 words)
- Extract trading signals from report content
- Calculate confidence scores for each signal
- Apply fallback keyword-matching extraction if LLM analysis fails
- Return structured response with analysis results

**Trading Signal Extraction:**
- Identify BUY, SELL, or HOLD actions from report content
- Extract symbol/ticker information
- Extract entry price and target price for each signal
- Extract stop-loss price for each signal
- Identify timeframe (e.g., short-term, medium-term, long-term)
- Assign confidence score (0.9=explicit, 0.6=implied, 0.3=passing mention)
- Store signals as JSON in database

**AI Provider Management:**
- Support multiple LLM providers (Claude/Groq)
- Use ANTHROPIC_API_KEY from environment as primary option
- Fall back to GROQ_API_KEY if Anthropic not configured
- Track which API provider was used for each analysis
- Handle API failures gracefully with fallback extraction

**Market Insights Extraction:**
- Extract key market insights mentioned in the report
- Identify symbols/tickers referenced
- Extract any price targets mentioned
- Include in summary output

**Data Persistence:**
- Store completed analyses in database
- Do NOT store failed analyses
- Record: analysis ID, report_id, summary text, trading_signals JSON, api_provider used, creation timestamp
- Keep raw_extracted_text separate from stored analysis

**Error Handling:**
- If LLM analysis fails (timeout, API error, rate limit, invalid response): do NOT store failure, proceed to fallback keyword-matching extraction
- Fallback extraction should identify basic signals using simple keyword matching
- Log failures with context for debugging

### Reusability Opportunities

**Code Patterns to Reference:**
- Config class pattern from `services/playwright-scraper/` for managing LLM provider configuration
- Custom exceptions pattern for AI-specific errors
- FastAPI service structure for consistency with existing microservices
- Async operation patterns for API calls
- Error handling and logging patterns used in scraper service

**Backend Patterns:**
- Service initialization pattern (Config, logger, database connection)
- Pydantic models for request/response validation
- Structured logging with context information
- Database interaction patterns (cursor management, transactions)

### Scope Boundaries

**In Scope:**
- LLM-based analysis of single report content
- Trading signal extraction (action, symbol, prices, timeframe, confidence)
- Executive summary generation (200-300 words)
- Market insights and symbols extraction
- Confidence score calculation
- API provider selection and fallback
- Fallback keyword-matching extraction on LLM failure
- Data storage of completed analyses
- Error handling and logging
- 1-2 unit tests for core functionality

**Out of Scope:**
- Trend analysis across multiple reports
- Portfolio aggregation
- Risk assessment across positions
- Multi-report correlation analysis
- Analyst credibility scoring
- Historical analysis tracking/trending
- Real-time market data integration
- Performance backtesting
- Advanced machine learning models
- Caching or optimization of analyses

### Technical Considerations

**Integration Points:**
- Receives: raw_extracted_text from content extraction service (stored in reports table)
- Sends: analysis results to database (analyses table)
- Consumes: External LLM APIs (Anthropic Claude or Groq)
- Dependencies: PostgreSQL database, environment variables for API keys

**Existing System Constraints:**
- Must use FastAPI for consistency with other services
- Must support async operations (FastAPI async pattern)
- Must run in Docker container with Python 3.11+
- Must use PostgreSQL for data persistence
- Must follow project's error handling standards
- Must support N8N workflow orchestration integration

**Technology Preferences Stated:**
- Python 3.11+
- FastAPI framework
- PostgreSQL database
- Support both Anthropic Claude and Groq APIs
- Pydantic for validation

**Similar Code Patterns to Follow:**
- Service structure from `services/playwright-scraper/`
- Config management pattern
- Custom exceptions pattern
- FastAPI route organization
- Async/await patterns for external API calls
- Structured error responses with error codes and messages

**Database Considerations:**
- Minimal schema approach (only essential fields)
- analyses table with: id, report_id, summary, trading_signals (JSON), api_provider, created_at
- Foreign key relationship to reports table
- Index on report_id for query performance
- No tracking of failed analyses

**API Design Considerations:**
- Keep raw_extracted_text separate from analysis in response
- Include api_provider information in response for transparency
- Structured trading signals response as array of signal objects
- Confidence scores as decimal values (0.0-1.0)
- Clear error responses when analysis cannot be performed
