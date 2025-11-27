# Spec Shaping Summary

## Status: Requirements Complete

Requirements gathering for Content Extraction & HTML Parsing feature is complete. All clarifying questions have been answered and requirements are documented comprehensively.

## Key Decisions Made

### Database Storage Strategy
- **Decision:** Add JSONB field `extracted_images` to existing `reports` table
- **Rationale:** Keeps image metadata with report data, avoids additional table joins
- **Structure:** Array of objects containing url, content_type, position_index, base64_data, is_tradingview

### Image Handling Approach
- **TradingView Charts:** Store as external URLs only (no download)
- **Regular Images:** Download and encode as base64, store in JSONB field
- **Detection Method:** URL pattern matching for TradingView domains

### Content Filtering Philosophy
- **In Scope:** Technical filtering (scripts, CSS, navigation, interactive elements)
- **Out of Scope:** Promotional content detection - delegated to AI analysis phase
- **Rationale:** Promotional patterns vary; AI is better suited for semantic filtering

### Error Handling Priority
- **Primary:** Extract clean semantic HTML
- **Fallback 1:** Strip HTML tags to plain text
- **Fallback 2:** Store raw HTML
- **Guarantee:** Never lose data, always store something

## Technical Architecture

### Portal Support
- **MVP Scope:** ProTradingSkills only (hardcoded selectors)
- **Future:** Multi-portal support via configuration (Phase 2+)

### CSS Selectors (ProTradingSkills)
```
Author: .avatar-info-component-container .name
Date: .avatar-info-component-container .text-info
Article: article.pts-analysis .entry-content
Title: .entry-content h2:first-of-type
Images: .entry-content img
Filter: .return-button-container, .button-like, script, style, meta, link
```

### Semantic HTML Output Tags
- Allowed: h1, h2, p, img, strong, em, ul, li, a
- All other tags stripped or filtered

### Date Parsing
- Input Format: Spanish ("26 de noviembre de 2025 a las 15:44")
- Output Format: UTC timestamp
- Library: python-dateutil or babel

## Integration Points

### Existing Services to Leverage
1. **Playwright Scraper Service** (`services/playwright-scraper/`)
   - Extend with new content extraction module
   - Reuse browser automation setup

2. **Email Webhook Service** (`services/email-webhook/`)
   - Database models and connection patterns
   - System logging utilities
   - Error handling patterns

3. **PostgreSQL Database**
   - `reports` table (add `extracted_images` JSONB field)
   - `system_logs` table (log extraction events)

### Workflow Position
```
Email Received → Webhook → Playwright Scrapes Page →
[NEW: Content Extraction] → AI Analysis → Notifications
```

## Database Schema Changes Required

### New Field in `reports` Table
```sql
ALTER TABLE reports ADD COLUMN extracted_images JSONB DEFAULT '[]';
```

### JSONB Structure
```json
[
  {
    "url": "https://example.com/image.png",
    "content_type": "image/png",
    "position_index": 0,
    "base64_data": "iVBORw0KGgo...",
    "is_tradingview": false,
    "width": 800,
    "height": 600
  }
]
```

### Existing Fields Usage
- `raw_html`: Stores original scraped HTML (audit trail)
- `extracted_text`: Stores clean semantic HTML output
- `status`: Manages processing state (pending → processing → completed/failed)

## Success Metrics

### Accuracy Targets
- Author extraction: 100%
- Date parsing: 100%
- Content extraction: 95%+
- Image identification: 100%
- Image download: 90%+

### Performance Targets
- Content extraction: <5 seconds
- Image downloads: <10 seconds per image
- Total processing: <30 seconds per report

### Quality Targets
- Valid semantic HTML output
- Zero JavaScript/CSS in output
- Complete removal of navigation elements
- Preserved text formatting
- Maintained image sequence

## Risks & Mitigations

### Risk: ProTradingSkills Changes HTML Structure
- **Mitigation:** Log extraction failures, implement monitoring alerts
- **Fallback:** Manual review queue for failed extractions

### Risk: Image Download Failures
- **Mitigation:** Retry logic with exponential backoff
- **Fallback:** Store URL only if download fails after retries

### Risk: Malformed HTML Breaks Parser
- **Mitigation:** Graceful degradation to plain text
- **Fallback:** Store raw HTML for manual review

### Risk: Date Parsing Fails
- **Mitigation:** Store original date string in metadata
- **Fallback:** Use report creation timestamp

## Out of Scope (Future Enhancements)

- Multi-portal support (Phase 2)
- Configurable extraction rules (Phase 2)
- OCR text extraction from images (Phase 3)
- PDF report processing (Phase 3)
- Video content extraction (Phase 4+)
- Real-time monitoring without webhook trigger (Phase 4+)

## Next Steps for Spec Writer

1. **Review Requirements:** Read `requirements.md` thoroughly
2. **Study Database Schema:** Review PostgreSQL spec for `reports` table structure
3. **Examine Existing Services:** Look at email-webhook and playwright-scraper patterns
4. **Design Extraction Module:** Create detailed module architecture
5. **Define API Contracts:** Specify function signatures and data flows
6. **Write Implementation Plan:** Break down into tasks with dependencies
7. **Document Edge Cases:** Specify behavior for all edge cases identified
8. **Create Test Scenarios:** Define comprehensive test cases

## Questions for Spec Writer to Address

1. Should image download happen synchronously or asynchronously (parallel)?
2. What's the retry strategy for failed image downloads (count, backoff)?
3. Should we validate image file integrity after download?
4. What's the maximum image size limit (if any)?
5. How to handle relative image URLs (base URL resolution)?
6. Should we cache downloaded images to avoid re-downloading?
7. What HTML parser library (BeautifulSoup vs lxml vs html5lib)?
8. How granular should extraction logging be (debug vs info)?

## References

- **Requirements Document:** `planning/requirements.md`
- **Product Mission:** `/agent-os/product/mission.md`
- **Product Roadmap:** `/agent-os/product/roadmap.md` (Item 4)
- **Tech Stack:** `/agent-os/product/tech-stack.md`
- **Database Schema:** `/agent-os/specs/2025-11-25-postgresql-schema-data-persistence/spec.md`
- **Existing Scraper:** `/services/playwright-scraper/`
- **Email Webhook:** `/services/email-webhook/`

---

**Status:** Ready for specification writing phase
**Date Completed:** 2025-11-27
**Requirements Researcher:** Claude Code
