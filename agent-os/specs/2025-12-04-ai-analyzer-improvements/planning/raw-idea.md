# Raw Idea: AI Analyzer Service Improvements

## User Description

The user has identified these issues with the current AI analyzer service:

1. Model is hardcoded in provider.py instead of using .env configuration
2. Prompt requires JSON response format which is suboptimal for LLM reasoning
3. LLMs perform better with streaming responses and thinking processes
4. Database should focus on storing: the report itself and proposed trading operations (which may be optional)
5. Trading operations include: long positions, short positions, options strategies, etc.

## Context

The AI analyzer service currently processes trading reports and needs improvements to:
- Make it more configurable (externalize model selection)
- Optimize LLM reasoning capabilities (remove JSON constraints)
- Improve response quality (leverage streaming and thinking)
- Refine data storage (focus on reports and trading operations)

## Expected Outcomes

- More flexible model configuration via environment variables
- Better LLM reasoning by allowing natural language responses
- Enhanced response quality through streaming and thinking processes
- Cleaner database schema focused on core entities (reports and trading operations)
