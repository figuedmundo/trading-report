# Spec Requirements: Content Extraction & HTML Parsing

## Initial Description

From raw-idea.md:

Roadmap Item 4 - Simplified content extraction for trading reports. The system needs to extract clean, relevant content from web pages containing trading reports, specifically focusing on extracting meaningful content while filtering out scripts, metadata, navigation elements, and other non-essential HTML.

Context:
- The only report format to support is a web page with a specific HTML structure
- Need to extract only the actual report content (author info, date, main content with text and images)
- Must filter out: scripts, metadata, navigation elements, like buttons, promotional content
- Example shows a trading analysis report from ProTradingSkills platform

## Requirements Discussion

### First Round Questions

**Q1:** For the database storage, I'm assuming we should store the extracted content in the existing `reports.raw_content` field (as clean semantic HTML), and add a new JSONB field to `reports` table for image metadata. Is that correct, or would you prefer a separate table for extracted content?

**Answer:** Option B - Add a JSONB field to the existing `reports` table containing image metadata + base64 encoded data

**Q2:** For filtering promotional content, I'm thinking we implement keyword-based detection (e.g., "promoción", "descuento", "oferta") to identify and exclude promotional sections. Should we do this, or is there a specific pattern to promotional content in ProTradingSkills reports?

**Answer:** If it's difficult to detect promotional content (because it can change), leave that task for the AI to handle during analysis phase. Do NOT implement keyword-based filtering for promotional content.

**Q3:** For error handling, if we fail to extract clean semantic HTML, should we: (A) Fall back to storing raw HTML, (B) Strip all HTML tags and store plain text, or (C) Try option B first, then fall back to option A?

**Answer:** Option C - Try stripping HTML tags to plain text first (Option B), if that fails use raw HTML (Option A)

**Q4:** For TradingView chart images (which are hosted on TradingView's CDN), should we: (A) Download and store them as base64 in our database, or (B) Keep them as external URLs to save space (they're on a reliable CDN)?

**Answer:** Option B - Keep as external URLs (save space, they're on reliable CDN)

**Q5:** For the date format shown in your example ("26 de noviembre de 2025 a las 15:44"), I assume we need to parse Spanish date formats. Should we convert this to UTC timestamp for storage?

**Answer:** Yes (implied from context and standard practices)

**Q6:** Are there any specific sections or elements you want to EXCLUDE from extraction beyond the ones mentioned (scripts, CSS, navigation, like buttons)?

**Answer:** No additional exclusions mentioned beyond the standard filters

### Existing Code to Reference

Based on user's response about similar features:

**Similar Features Identified:**
- Playwright scraper service: `/Users/edmundo.figueroaherbas@medirect.com.mt/projects/personal/trading-report/services/playwright-scraper/` (contains existing browser automation patterns)
- Email webhook service: `/Users/edmundo.figueroaherbas@medirect.com.mt/projects/personal/trading-report/services/email-webhook/` (contains database models and integration patterns)
- Database schema: Already defined in PostgreSQL Schema spec (reports table, report_images table)

**Components to potentially reuse:**
- Playwright browser automation setup and configuration
- Database connection and models from email-webhook service
- Error handling patterns from existing services
- System logging utilities

**Backend logic to reference:**
- Database models in `services/email-webhook/src/models.py`
- Database operations in `services/email-webhook/src/database.py`
- System logging in `services/email-webhook/src/system_logging.py`

### Follow-up Questions

None needed - all requirements clarified through initial round.

## Visual Assets

### Files Provided:
No visual assets provided.

### Visual Insights:
No visual mockups or wireframes were provided. Implementation will be based on:
- ProTradingSkills HTML structure (CSS selectors provided by user)
- Clean semantic HTML output requirements
- Database schema from PostgreSQL spec

## Requirements Summary

### Functional Requirements

**Core Content Extraction:**
- Extract author name from `.avatar-info-component-container .name` CSS selector
- Extract publication date from `.avatar-info-component-container .text-info` (Spanish format)
- Extract article title from `.entry-content h2` (first h2 element)
- Extract main article content from `article.pts-analysis .entry-content`
- Extract images from `.entry-content img` elements

**Content Filtering:**
- Remove JavaScript code (`<script>` tags and inline JavaScript)
- Remove CSS stylesheets (`<style>` tags and inline CSS)
- Remove navigation elements (`.return-button-container`)
- Remove interactive elements (`.button-like`, like buttons, share buttons)
- Remove metadata tags (`<meta>`, `<link>`)
- Preserve ONLY semantic HTML tags: `<h1>`, `<h2>`, `<p>`, `<img>`, `<strong>`, `<em>`, `<ul>`, `<li>`, `<a>`

**Image Handling:**
- Download non-TradingView images and convert to base64
- Store TradingView chart URLs as external references (do NOT download)
- Detect TradingView images by URL pattern matching (e.g., contains "tradingview.com")
- Replace downloaded image URLs with local references in extracted HTML
- Maintain image sequence order within report

**Date Parsing:**
- Parse Spanish date format: "26 de noviembre de 2025 a las 15:44"
- Convert to UTC timestamp for storage
- Handle month names in Spanish (enero, febrero, marzo, abril, mayo, junio, julio, agosto, septiembre, octubre, noviembre, diciembre)

**Output Format:**
- Clean semantic HTML with only meaningful tags
- Easily convertible to Markdown for AI analysis later
- Well-formed HTML structure (proper nesting, closed tags)
- Preserve text formatting (bold, italic, lists)
- Preserve link destinations and anchor text

**Portal Configuration:**
- Hardcoded extraction logic for ProTradingSkills only
- No configurable per-portal settings needed for MVP
- CSS selectors specific to ProTradingSkills HTML structure

### Reusability Opportunities

**Database Models & Connection:**
- Reuse SQLAlchemy models from `services/email-webhook/src/models.py`
- Reuse database connection utilities from `services/email-webhook/src/database.py`
- Follow existing patterns for transaction management and error handling

**Playwright Integration:**
- Extend existing Playwright scraper service at `services/playwright-scraper/`
- Reuse browser automation setup and configuration
- Add new content extraction module to existing service

**System Logging:**
- Use system_logging utility from `services/email-webhook/src/system_logging.py`
- Follow existing event-based logging patterns
- Log extraction events with metadata (duration, images found, content length)

**Error Handling:**
- Follow error handling patterns from email-webhook service
- Use existing retry logic patterns
- Maintain consistency with database status updates

### Scope Boundaries

**In Scope:**
- HTML content extraction from ProTradingSkills reports
- Image downloading and base64 encoding (except TradingView)
- Spanish date parsing and UTC conversion
- Clean semantic HTML output
- Database schema updates (new JSONB field for images)
- Integration with existing playwright-scraper service
- Error handling with fallback strategies

**Out of Scope:**
- Multi-portal support (only ProTradingSkills for MVP)
- Promotional content filtering (delegated to AI analysis phase)
- OCR text extraction from images
- PDF report extraction
- Email attachment parsing
- Video or audio content extraction
- Configurable portal-specific rules (hardcoded for now)
- Real-time report monitoring (webhook-triggered only)

### Technical Considerations

**Database Schema Updates:**
- Add JSONB field to `reports` table: `extracted_images` containing array of image metadata objects
- Image metadata structure:
  ```json
  {
    "url": "original_url or 'local'",
    "content_type": "image/png",
    "position_index": 0,
    "base64_data": "iVBORw0KGgo..." // for non-TradingView images only
    "is_tradingview": false,
    "width": 800,  // optional
    "height": 600  // optional
  }
  ```
- Retain existing `raw_html` field for audit purposes
- Use `extracted_text` field for clean semantic HTML output

**Integration with Playwright Scraper:**
- Extend scraper service to include content extraction module
- Call extraction after page load and authentication
- Update `reports` table with extracted content and images
- Log extraction events to `system_logs` table

**Error Handling Strategy:**
1. Primary: Try to extract clean semantic HTML
2. Fallback 1: Strip all HTML tags, store plain text in `extracted_text`
3. Fallback 2: Store raw HTML in `raw_html` field
4. Always log extraction failures with error details

**Spanish Date Parsing:**
- Use locale-aware parsing library (e.g., babel, dateutil)
- Map Spanish month names to numeric months
- Parse time component (hours and minutes)
- Convert to UTC timezone (assume local timezone is Europe/Madrid for ProTradingSkills)

**CSS Selectors for ProTradingSkills:**
```python
SELECTORS = {
    "author": ".avatar-info-component-container .name",
    "date": ".avatar-info-component-container .text-info",
    "article": "article.pts-analysis .entry-content",
    "title": ".entry-content h2:first-of-type",
    "images": ".entry-content img",
    "filter_out": [
        ".return-button-container",
        ".button-like",
        "script",
        "style",
        "meta",
        "link"
    ]
}
```

**Image Detection Patterns:**
```python
TRADINGVIEW_PATTERNS = [
    "tradingview.com",
    "tradingview.net",
    "tv.com"
]

def is_tradingview_image(url: str) -> bool:
    return any(pattern in url.lower() for pattern in TRADINGVIEW_PATTERNS)
```

**Technology Stack:**
- Python 3.11+
- Playwright for browser automation
- Beautiful Soup 4 or lxml for HTML parsing
- SQLAlchemy for database operations
- Python-dateutil or babel for date parsing
- Base64 module (stdlib) for image encoding

**Dependencies:**
- playwright (already in use)
- beautifulsoup4 or lxml (for HTML parsing)
- python-dateutil (for Spanish date parsing)
- pillow (for image processing/validation)
- requests or httpx (for image downloading)

**Integration Points:**
- Triggered by N8N workflow after successful page load
- Reads from `reports` table (status='processing')
- Writes to `reports` table (`extracted_text`, `extracted_images` JSONB, status='processing')
- Writes to `system_logs` table (extraction events)
- Proceeds to AI analysis phase after successful extraction

### Success Criteria

**Extraction Accuracy:**
- 100% of author names extracted correctly
- 100% of dates parsed and converted to UTC
- 95%+ of main content text extracted without loss
- 100% of images identified and categorized (TradingView vs. regular)
- 90%+ of non-TradingView images downloaded successfully

**Output Quality:**
- Semantic HTML is well-formed and valid
- All JavaScript and CSS removed from output
- Navigation and interactive elements fully removed
- Image references properly maintained in HTML
- Text formatting preserved (bold, italic, lists, links)

**Performance:**
- Content extraction completes within 5 seconds (not including page load)
- Image downloads complete within 10 seconds per image
- Total extraction time < 30 seconds per report (including image downloads)

**Error Handling:**
- Graceful degradation to plain text when HTML extraction fails
- Raw HTML fallback when plain text extraction fails
- Detailed error logging for troubleshooting
- No data loss (always store something, even if raw HTML)

**Database Integration:**
- JSONB field properly populated with image metadata
- No constraint violations or transaction failures
- Proper status transitions (processing → completed or failed)
- System logs capture all extraction events

### Edge Cases to Handle

**HTML Parsing:**
- Malformed HTML (unclosed tags, invalid nesting)
- Empty content sections
- Missing author or date information
- Duplicate image references
- Relative image URLs (need to convert to absolute)

**Image Processing:**
- Image download failures (404, timeout, network errors)
- Large images (>10MB) - may need size limits
- Unsupported image formats
- Broken image URLs
- CORS or authentication-protected images

**Date Parsing:**
- Unexpected date formats
- Missing time component
- Invalid dates (e.g., "32 de enero")
- Timezone ambiguity

**Content Filtering:**
- Nested promotional content within main article
- Dynamic content loaded via JavaScript (may be missing)
- Iframes or embedded content
- Social media embeds

### Testing Requirements

**Unit Tests:**
- Test Spanish date parsing with various formats
- Test TradingView URL detection
- Test HTML cleaning and semantic tag preservation
- Test image base64 encoding
- Test CSS selector matching

**Integration Tests:**
- Test full extraction workflow with sample ProTradingSkills page
- Test database updates (JSONB field population)
- Test error fallback sequence (semantic HTML → plain text → raw HTML)
- Test system logging integration

**Edge Case Tests:**
- Test with missing author or date
- Test with no images
- Test with only TradingView images
- Test with malformed HTML
- Test with failed image downloads

**Performance Tests:**
- Measure extraction time with various content sizes
- Measure image download time with multiple images
- Verify memory usage with large reports

**Regression Tests:**
- Verify existing scraper functionality not broken
- Verify database schema compatibility
- Verify N8N workflow integration still works
