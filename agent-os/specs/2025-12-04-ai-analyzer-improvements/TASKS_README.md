# AI Analyzer Service Improvements - Implementation Tasks

## Quick Start

This document contains the complete implementation plan for the AI Analyzer Service improvements specification. It is organized into 8 implementation phases with 18 task groups and 45+ detailed subtasks.

**File**: `tasks.md` (1,400 lines)
**Estimated Effort**: 107-133 hours
**Timeline**: 12 days (or 6-8 days with parallel development)

## Organization

The tasks list is organized as follows:

### Phase 1: Foundation (1 task group, 3 subtasks)
- Configuration management for LLM_MODEL and THINKING_BUDGET_TOKENS
- Provider detection utility function
- Critical path: must complete before other work

### Phase 2: Provider Enhancement (4 task groups, 22 subtasks)
- Anthropic provider with extended thinking
- Groq provider with graceful thinking degradation  
- Google Gemini provider (new)
- Factory pattern integration
- Can be parallelized across developers

### Phase 3: Markdown Parsing (1 task group, 6 subtasks)
- Markdown section extraction utilities
- Trading operations JSON parsing
- Can be done in parallel with Phase 2

### Phase 4: Database & Models (3 task groups, 17 subtasks)
- Database migration (4 new columns, 4 new indexes)
- Pydantic model updates
- Repository/database layer updates
- Must follow Phase 1, can follow Phase 3 in parallel

### Phase 5: Service Integration (3 task groups, 17 subtasks)
- LLMAnalyzer orchestration layer
- AnalysisService workflow
- API routes and response formatting
- Depends on Phases 2-4

### Phase 6: Configuration Validation (1 task group, 4 subtasks)
- Startup configuration validation
- Health check enhancement
- Depends on Phases 1-5

### Phase 7: Testing (3 task groups, 25+ subtasks)
- Unit tests (8 files, 6-8 tests each)
- Integration tests (5 files, 4-6 tests each)  
- Test review and gap analysis
- Total: ~70-95 feature-focused tests
- Depends on Phases 1-6 implementation

### Phase 8: Documentation & Deployment (2 task groups, 11 subtasks)
- Documentation updates (README, API docs, guides)
- Final integration testing and deployment readiness
- Depends on all other phases

## Key Implementation Concepts

### Provider Factory Pattern
```
LLM_MODEL environment variable (e.g., "claude-3-5-sonnet-20241022")
    ↓ (model prefix detection)
Provider selection (Anthropic | Groq | Google)
    ↓ (API key validation)
Provider instantiation with thinking_budget_tokens
```

### Extended Thinking Flow
- Configuration: THINKING_BUDGET_TOKENS (default 5000, range 1000-32000)
- Anthropic: Full support with thinking content storage
- Groq: Graceful degradation (no thinking, log INFO)
- Google: Full support with streaming response buffering
- Storage: thinking_content (TEXT), thinking_tokens_used (INTEGER)

### Markdown Response Parsing
- Provider returns markdown text (not forced JSON)
- Parse sections: ## Summary, ## Market Analysis, ## Trading Operations, etc.
- Extract Trading Operations from JSON array in markdown
- Set operations_found boolean based on extraction result
- Graceful failure: parsing errors logged, don't break analysis

### Flexible JSONB Operations Storage
- Remove CHECK constraint on ai_provider column
- Support new providers: "google", "fallback", "hybrid", etc.
- Trading operations as flexible JSONB array (no type constraints)
- Allow undefined fields beyond core schema

### Database Schema Changes
- Add 4 columns: thinking_budget_tokens, thinking_tokens_used, thinking_content, operations_found
- Create 4 indexes for efficient querying
- Expand ai_provider VARCHAR(50) → VARCHAR(100)
- Backfill existing records with defaults (no data loss)

## Execution Strategy

### Sequential Tasks (Must Follow)
1. Phase 1 (Foundation) → All other phases blocked
2. Phase 2 (Providers) → All downstream phases blocked
3. Phase 3 (Parsing) → Can run parallel with Phase 2
4. Phase 4 (Database) → Depends on Phase 1, can follow Phase 3
5. Phase 5 (Integration) → Depends on Phase 2, 3, 4
6. Phase 6 (Configuration) → Depends on Phase 1-5
7. Phase 7 (Testing) → Depends on Phase 1-6
8. Phase 8 (Documentation) → Last phase, depends on all

### Parallel Tracks (With Multiple Developers)
- **Track A**: Phase 1 → Anthropic Provider → LLMAnalyzer
- **Track B**: Groq & Google Providers → Factory → Service Layer
- **Track C**: Markdown Parser → Database → Repository
- **Track D**: Testing (after implementations have checkpoints)

### Synchronization Points
- End of Phase 1: Configuration working for all
- End of Phase 2: All providers in factory
- End of Phase 3: Markdown parser ready
- End of Phase 4: Database and models complete
- End of Phase 5: Service integration complete
- Start Phase 7: Implementation complete, testing begins

## Testing Approach

### Minimal Testing During Development (Per Project Standards)
- Focus on feature completion during Phases 1-6
- Write minimal tests, only at logical completion points
- No tests for every change or intermediate step

### Comprehensive Testing in Phase 7
- **Unit Tests**: 8 files, 6-8 tests each (~50-65 tests)
  - Focus: Provider detection, markdown parsing, individual behaviors
  - Mocked dependencies, no real API calls
  
- **Integration Tests**: 5 files, 4-6 tests each (~20-30 tests)
  - Focus: End-to-end workflows, database, API response
  - Real database, mocked LLM providers
  
- **Gap-Filling Tests**: Maximum 5 additional tests
  - Fill critical gaps identified in review

- **Total**: ~70-95 focused tests (not comprehensive coverage)

### Coverage Focus
✓ Critical user workflows (provider detection, analysis, operations extraction)
✓ Database persistence and backward compatibility
✓ Configuration validation and error handling
✓ API response format and new fields

✗ Edge cases and boundary conditions
✗ Non-critical error scenarios
✗ Performance benchmarking (noted but not tested)
✗ Exhaustive field validation

## File Modifications Summary

### Code Files to Modify (9 files)
1. `services/ai-analyzer/src/config.py` - Config management
2. `services/ai-analyzer/src/llm/provider.py` - Providers and factory
3. `services/ai-analyzer/src/llm/analyzer.py` - LLM orchestration
4. `services/ai-analyzer/src/services/analysis_service.py` - Service layer
5. `services/ai-analyzer/src/models.py` - Pydantic models
6. `services/ai-analyzer/src/db/analyses_repository.py` - Database layer
7. `services/ai-analyzer/src/extraction/markdown_parser.py` - NEW
8. `services/ai-analyzer/.env.example` - Configuration docs
9. `database/migrations/014_ai_analyzer_improvements.sql` - NEW

### Test Files to Create (13 files)
- Unit tests: provider_detection, markdown_parser, anthropic, groq, google, llm_analyzer, analysis_service, config
- Integration tests: e2e_analysis, provider_switching, markdown_parsing, database_persistence, api_response

### Documentation Files (6 files)
- `services/ai-analyzer/README.md` - Service documentation
- `services/ai-analyzer/docs/API.md` - API documentation
- `database/migrations/README.md` - Migration guide
- `DEPLOYMENT_CHECKLIST.md` - Pre/post deployment checklist
- `DEPLOYMENT_NOTES.md` - Deployment guidance
- `RELEASE_NOTES.md` - Release summary

## Acceptance Criteria

Implementation complete when:

1. ✓ All 45 subtasks in task groups 1-18 checked off
2. ✓ All code passes `make lint`, `make typecheck`, `make format`
3. ✓ Database migration 014 runs without errors
4. ✓ Service starts with provider auto-detection logged
5. ✓ /api/v1/analyze returns AnalysisSuccessResponse with all new fields
6. ✓ ~70-95 feature-specific tests created and passing
7. ✓ Markdown parsing correctly extracts sections
8. ✓ Extended thinking tokens captured and stored
9. ✓ Backward compatibility verified (old data still accessible)
10. ✓ Documentation complete (README, API docs, deployment checklist)
11. ✓ Deployment checklist tested and verified

## How to Use This Document

1. **Start Here**: Read this README for overview
2. **Open tasks.md**: Detailed implementation guidance
3. **Follow Phases**: Execute in order (dependencies matter)
4. **Check Off Tasks**: Mark subtasks as completed
5. **Run Tests**: Phase 7 (after implementation)
6. **Deploy**: Phase 8 (verify checklist)
7. **Reference**: Acceptance criteria for verification

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Provider API changes | Abstract interface + version pins |
| Database migration failure | Test on staging first + rollback plan |
| Backward compat breaks | Keep existing columns, add with defaults |
| Configuration errors | Clear docs + startup validation + helpful messages |
| Incomplete provider handling | Comprehensive error handling + fallback |
| Large thinking storage | Configurable budget, database monitoring |

## Success Metrics

- All 45 subtasks completed
- All tests passing
- All code standards met
- Database migrated successfully
- Service starts and auto-detects provider
- All new features working (thinking, markdown parsing, flexible operations)
- Backward compatibility maintained
- Documentation complete and accurate
- Deployment checklist verified

## Next Steps

1. Read and understand the full `tasks.md` document
2. Plan parallel development tracks if working with team
3. Set up Phase 1 work (configuration)
4. Execute phases in order
5. Check off subtasks as completed
6. Run tests in Phase 7
7. Follow deployment checklist in Phase 8

---

**Version**: 1.0  
**Created**: December 4, 2025  
**Status**: Ready for Implementation
