# Specification: Content Extraction & HTML Parsing

## Goal

Extract clean, semantic HTML content from trading report web pages while intelligently handling images, filtering noise, and preserving meaningful structure. The extracted content will be optimized for downstream AI analysis and formatted for easy conversion to Markdown, with support for ProTradingSkills platform in MVP.

## User Stories

- As an analyst, I want automated extraction of clean trading report content without scripts, navigation, or promotional clutter so I can focus on analyzing actual trading data
- As an automation system, I want reliable image handling (downloading regular images, preserving TradingView links) with base64 storage for reproducibility and archival
- As an operator, I want graceful fallback behavior (clean HTML → plain text → raw HTML) so no data is lost even when extraction partially fails

## Specific Requirements

**Content Extraction & Filtering**
- Extract clean semantic HTML from ProTradingSkills reports using CSS selectors: author (`.avatar-info-component-container .name`), date (`.avatar-info-component-container .text-info`), title (`.entry-content h2:first-of-type`), and main content (`article.pts-analysis .entry-content`)
- Preserve only semantic HTML tags: `h1`, `h2`, `p`, `img`, `strong`, `em`, `ul`, `li`, `a` with proper nesting and closed tags
- Remove all technical noise: `<script>`, `<style>`, `<meta>`, `<link>` tags; inline JavaScript and CSS; and UI elements (`.return-button-container`, `.button-like`)
- Do NOT implement keyword-based filtering for promotional content—delegate to AI analysis phase (promotional patterns vary too much)
- Maintain text formatting (bold, italic, lists) and link destinations in extracted output

**Image Handling Strategy**
- Download non-TradingView images and store as base64 in JSONB `extracted_images` field (detect TradingView by URL pattern: `tradingview.com`, `tradingview.net`, `tv.com`)
- Keep TradingView chart URLs as external references only (no download, save database space, rely on CDN reliability)
- Replace downloaded image URLs with local references (`local://image-[index]`) in extracted HTML to enable offline-first processing
- Maintain image sequence order and metadata (width, height, content_type, MIME type) for reconstruction

**Date Parsing & Conversion**
- Parse Spanish date format: "26 de noviembre de 2025 a las 15:44" to UTC timestamp
- Handle all Spanish month names (enero, febrero, marzo, abril, mayo, junio, julio, agosto, septiembre, octubre, noviembre, diciembre)
- Assume local timezone is Europe/Madrid for ProTradingSkills (convert to UTC for storage)
- Store original date string in image metadata if parsing fails (graceful fallback)

**Database Schema Changes**
- Add `extracted_images JSONB DEFAULT '[]'` column to `reports` table
- Image metadata structure: `[{ "url", "content_type", "position_index", "base64_data" (non-TradingView only), "is_tradingview", "width", "height" }]`
- Retain existing `raw_html` field for audit trail and fallback storage
- Use `extracted_text` field for clean semantic HTML output

**Error Handling with Fallback Cascade**
- Primary strategy: Extract clean semantic HTML with CSS selectors
- Fallback 1 (if semantic extraction fails): Strip all HTML tags, store plain text in `extracted_text`
- Fallback 2 (if plain text extraction fails): Store raw HTML from `raw_html` field
- Never lose data—always store something (semantic HTML → plain text → raw HTML)
- Log all failures with error details for troubleshooting and pattern analysis

**Integration with Scraper Service**
- Extend existing Playwright scraper service at `services/playwright-scraper/`
- Call extraction module after successful page load and authentication, before status update
- Update `reports` table atomically: set `extracted_text`, `extracted_images` JSONB, update status
- Log extraction events to `system_logs` table with duration, images found, content length

**Portal Support & Configuration**
- MVP scope: ProTradingSkills only with hardcoded CSS selectors
- No configurable per-portal settings in MVP (single-portal support)
- Future phases can extend with multi-portal configuration table

## Visual Design

(No visual mockups provided for content extraction specification)

## Existing Code to Leverage

**Email Webhook Database Models** (`services/email-webhook/src/models.py`)
- Pydantic models pattern for request/response validation with field aliases and ConfigDict
- Use same BaseModel patterns for extraction input/output contracts
- Apply Field validation patterns (regex patterns for status enums)
- Reuse error response model structure for extraction failures

**System Logging Pattern** (`services/email-webhook/src/system_logging.py`)
- Event-based logging with correlation_id for distributed tracing across services
- Log events to PostgreSQL `system_logs` table with service_name, log_level, message, metadata
- Use JSONB metadata to capture contextual data (duration, images_found, content_length, errors)
- Follow fallback pattern when database unavailable (log to standard logging)

**Database Operations** (`services/email-webhook/src/database.py`)
- Connection pooling and transaction management patterns
- Parameterized SQL queries to prevent injection
- Error handling with specific exception types for connection vs query failures
- Use same database pool configuration for extraction service

**Error Handling Patterns**
- Specific exception types rather than generic Exception handling
- Graceful degradation when non-critical features fail (image download failure doesn't block text extraction)
- Exponential backoff for retryable failures (image download timeouts)
- Log errors with full traceback to system_logs table for debugging

## Content Extraction Rules

**CSS Selector Configuration (ProTradingSkills)**

```python
PROTRADING_SKILLS_SELECTORS = {
    "author": ".avatar-info-component-container .name",
    "date": ".avatar-info-component-container .text-info",
    "article": "article.pts-analysis .entry-content",
    "title": ".entry-content h2:first-of-type",
    "images": ".entry-content img",
}

FILTER_OUT_SELECTORS = [
    ".return-button-container",
    ".button-like",
    "script",
    "style",
    "meta",
    "link",
]

ALLOWED_TAGS = {"h1", "h2", "p", "img", "strong", "em", "ul", "li", "a"}
```

**Image Detection & Classification**

```python
TRADINGVIEW_PATTERNS = [
    "tradingview.com",
    "tradingview.net",
    "tv.com",
]

def is_tradingview_image(url: str) -> bool:
    """Check if image is hosted on TradingView CDN."""
    return any(pattern in url.lower() for pattern in TRADINGVIEW_PATTERNS)
```

**Spanish Month Mapping**

```python
SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# Date format: "26 de noviembre de 2025 a las 15:44"
# Parse as: day de month de year a las hour:minute
```

**Semantic Tag Preservation**

- Preserve text content and attributes for allowed tags
- Strip attributes from tags except: `href` (for `<a>`), `src`/`alt` (for `<img>`)
- Normalize whitespace (collapse multiple spaces/newlines)
- Ensure proper tag nesting and closure
- Convert relative URLs to absolute URLs for links (use page base URL as reference)

**Edge Cases & Handling**

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Malformed HTML | Use permissive parser (BeautifulSoup with `html.parser` backend), fix unclosed tags automatically |
| Missing author or date | Log WARNING, continue extraction with available data, store NULL in database |
| No images found | Set `extracted_images` to empty array `[]`, no fallback needed |
| Empty content sections | Log INFO event, store what was extracted (may be partial) |
| Relative image URLs | Convert to absolute using page base URL, validate URL format before download |
| Duplicate images | Keep in sequence order, allow duplicates (deduplication delegated to later phases) |
| Dynamic content missing | Extract static DOM content only, no JavaScript execution for additional content (JavaScript already removed) |

## Image Handling

**Image Download Workflow**

```
For each <img> in article.pts-analysis .entry-content:
  1. Extract src URL
  2. Validate URL format (http/https)
  3. Check if TradingView URL
     ├─ YES: Store URL reference only, set is_tradingview=true, skip download
     └─ NO: Proceed to download
  4. Download image with timeout (10 seconds per image)
  5. Validate image integrity (check MIME type, minimum size 100 bytes)
  6. Encode to base64
  7. Store in extracted_images JSONB array
  8. In extracted HTML, replace src="original-url" with src="local://image-0"
  9. On failure: Log WARNING, store URL reference instead of base64, continue
```

**Image Metadata Structure**

```json
[
  {
    "url": "https://example.com/chart.png",           // Original URL or "local" for downloaded
    "content_type": "image/png",                       // MIME type from response header
    "position_index": 0,                               // Sequential order in article
    "base64_data": "iVBORw0KGgo...[truncated]...",    // Base64 only if downloaded
    "is_tradingview": false,                          // TradingView URL flag
    "width": 800,                                      // Image dimensions (optional)
    "height": 600,
    "download_status": "success"                       // success | failed | tradingview_link
  },
  {
    "url": "https://tradingview.com/chart/...",      // TradingView URL
    "content_type": "text/html",
    "position_index": 1,
    "is_tradingview": true,
    "download_status": "tradingview_link",
    "base64_data": null                               // NOT populated for TradingView
  }
]
```

**Image Download Configuration**

- Timeout per image: 10 seconds
- Retry strategy: 2 retries with exponential backoff (1s, 2s) for transient failures (timeout, connection reset)
- Max image size: 5MB (skip images larger than this, log WARNING)
- Supported formats: image/png, image/jpeg, image/webp, image/gif
- Reject other MIME types with WARNING log
- Parallel downloads: Up to 3 concurrent image downloads per report (balance speed vs resource usage)

**URL Replacement in HTML**

```python
# Original: <img src="https://example.com/image-0.png" alt="Chart"/>
# Becomes:  <img src="local://image-0" alt="Chart"/>
# This enables offline-first processing and reduces message size for AI analysis
```

## Database Integration

**SQL Operations**

```sql
-- Insert/Update report with extracted content
UPDATE reports
SET
  extracted_text = 'clean semantic HTML...',  -- Primary output
  extracted_images = '[{"url": ..., "base64_data": ...}, ...]'::jsonb,
  status = 'processing',  -- After extraction, before AI analysis
  metadata = jsonb_set(
    metadata,
    '{extraction_duration_ms}',
    '2150'
  ),
  updated_at = NOW()
WHERE id = $1;

-- Log extraction event
INSERT INTO system_logs (
  service_name,
  log_level,
  message,
  report_id,
  correlation_id,
  metadata
) VALUES (
  'content_extraction',
  'INFO',
  'Content extraction completed successfully',
  $1,
  $2,
  jsonb_build_object(
    'duration_ms', 2150,
    'images_found', 2,
    'tradingview_images', 1,
    'content_length_bytes', 15340,
    'author_extracted', true,
    'date_parsed', true
  )
);
```

**Error Handling & Logging**

```sql
-- Log extraction failure with fallback used
INSERT INTO system_logs (
  service_name,
  log_level,
  message,
  report_id,
  correlation_id,
  metadata,
  stack_trace
) VALUES (
  'content_extraction',
  'WARNING',
  'Semantic HTML extraction failed, fell back to plain text',
  $1,
  $2,
  jsonb_build_object(
    'extraction_attempt', 'semantic_html',
    'fallback_used', 'plain_text',
    'error', 'Invalid CSS selector match',
    'images_downloaded', 1,
    'content_length_bytes', 8920
  ),
  $3  -- Python traceback
);
```

## API/Interface Design

**Extraction Service Module Interface**

```python
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ExtractionResult:
    """Result of content extraction operation."""
    success: bool
    extracted_text: Optional[str]  # Clean semantic HTML or plain text fallback
    extracted_images: List[Dict[str, Any]]  # Image metadata + base64 data
    author: Optional[str]
    publication_date: Optional[datetime]
    title: Optional[str]
    fallback_used: Optional[str]  # None | "plain_text" | "raw_html"
    error_message: Optional[str]
    duration_ms: int
    images_downloaded: int
    images_failed: int

class ContentExtractor:
    """Extract clean content from trading report HTML."""

    async def extract_from_html(
        self,
        html: str,
        report_url: str,
        page_base_url: str,
        correlation_id: str,
    ) -> ExtractionResult:
        """
        Extract clean semantic HTML from report page.

        Args:
            html: Raw HTML content from page
            report_url: Original report URL (for logging)
            page_base_url: Base URL for relative link resolution
            correlation_id: Distributed trace ID

        Returns:
            ExtractionResult with extracted content or fallback
        """
        pass

    async def parse_spanish_date(date_string: str) -> Optional[datetime]:
        """
        Parse Spanish date format "26 de noviembre de 2025 a las 15:44".
        Returns UTC timestamp or None if parsing fails.
        """
        pass

    async def download_image(
        self,
        image_url: str,
        timeout: int = 10,
        max_retries: int = 2,
    ) -> Optional[Dict[str, Any]]:
        """
        Download and encode image to base64 if not TradingView.
        Returns image metadata dict or None on failure.
        """
        pass

class ExtractionConfig:
    """Configuration for extraction behavior."""
    # Selectors
    author_selector: str = ".avatar-info-component-container .name"
    date_selector: str = ".avatar-info-component-container .text-info"
    article_selector: str = "article.pts-analysis .entry-content"
    title_selector: str = ".entry-content h2:first-of-type"
    image_selector: str = ".entry-content img"
    filter_selectors: List[str] = [
        ".return-button-container",
        ".button-like",
        "script",
        "style",
    ]

    # Image handling
    max_image_size_mb: int = 5
    image_download_timeout_s: int = 10
    image_download_retries: int = 2
    parallel_image_downloads: int = 3

    # Allowed semantic tags
    allowed_html_tags: set = {"h1", "h2", "p", "img", "strong", "em", "ul", "li", "a"}
```

**Integration with Scraper Service**

```python
# In playwright-scraper service, after page load:

from content_extraction import ContentExtractor, ExtractionConfig

config = ExtractionConfig()
extractor = ContentExtractor(config)

# After successful page load and authentication
html_content = page.content()  # From Playwright page object
extraction_result = await extractor.extract_from_html(
    html=html_content,
    report_url=report_url,
    page_base_url=page.url,
    correlation_id=correlation_id,
)

if extraction_result.success:
    # Update report with extracted content
    db.update_report(
        report_id=report_id,
        extracted_text=extraction_result.extracted_text,
        extracted_images=extraction_result.extracted_images,
        metadata={
            "extraction_duration_ms": extraction_result.duration_ms,
            "images_downloaded": extraction_result.images_downloaded,
        }
    )
    log_event(
        "INFO",
        "Content extraction completed",
        extracted_images=len(extraction_result.extracted_images),
        fallback_used=extraction_result.fallback_used,
    )
else:
    log_event(
        "ERROR",
        "Content extraction failed",
        error=extraction_result.error_message,
        fallback=extraction_result.fallback_used,
    )
```

## Success Criteria

**Extraction Accuracy**
- Author name extracted correctly: 100% of test cases
- Publication date parsed and converted to UTC: 100% of Spanish format dates
- Main content text extracted without loss: 95%+ preservation (allow minor whitespace normalization)
- All article images identified: 100% of `<img>` tags within content area
- TradingView vs regular images correctly classified: 100%
- Non-TradingView images downloaded successfully: 90%+ (allow for transient network failures)

**Output Quality**
- Extracted semantic HTML is well-formed: All tags properly nested and closed, validates with HTML parser
- Zero JavaScript in output: No `<script>` tags or `javascript:` protocols in attributes
- Zero CSS in output: No `<style>` tags or inline `style` attributes
- Navigation elements fully removed: No `.return-button-container`, `.button-like` classes present
- Image references maintained: All images referenced with either base64 data or `local://` URLs
- Text formatting preserved: Bold, italic, lists, links all maintained in output

**Performance**
- Content extraction (HTML parsing): < 2 seconds per report
- Image downloads: < 10 seconds per image (with parallel downloads: total < 20 seconds for up to 3 images)
- Total extraction time (including all images): < 30 seconds per report
- Memory usage: < 200MB peak per report (large HTML documents + base64 encoding)

**Error Handling & Resilience**
- Graceful degradation to plain text: Works when semantic HTML extraction fails
- Further fallback to raw HTML: Works when plain text extraction fails
- No data loss: Always stores something, even raw HTML
- Detailed error logging: All failures logged with error details, correlation ID, stack trace
- Retry logic: Image download failures automatically retried up to 2 times

**Database & Integration**
- `extracted_images` JSONB field populated correctly: All image metadata present and valid JSON
- `extracted_text` field populated: Clean HTML or fallback text stored
- `raw_html` field retained: Original HTML preserved for audit trail
- System logs recorded: All events logged with service_name, log_level, metadata
- No constraint violations: Report status transitions valid, foreign keys maintained

## Implementation Phases

**Phase 1: Core Extraction (MVP)**
1. HTML parsing with BeautifulSoup 4
2. CSS selector-based extraction (author, date, title, content)
3. Semantic tag filtering (preserve h1-h2-p-strong-em-ul-li-a)
4. Spanish date parsing to UTC
5. Image detection (TradingView vs regular)
6. Image downloading and base64 encoding
7. Error fallback cascade (semantic → plain text → raw HTML)
8. Integration with existing Playwright scraper service
9. System logging to PostgreSQL

**Phase 2: Optimization & Robustness (Post-MVP)**
1. Image deduplication by hash
2. Configurable per-portal CSS selectors
3. Advanced image validation (dimensions, aspect ratio)
4. Caching of extracted content for duplicate reports
5. Performance monitoring and metrics

**Phase 3: Advanced Features**
1. Multi-language date parsing (extend beyond Spanish)
2. OCR text extraction from images
3. Structured data extraction (tables, metrics)
4. Content versioning and re-extraction

## Risks & Mitigations

**Risk 1: ProTradingSkills Changes HTML Structure**
- Impact: CSS selectors no longer match, content extraction fails
- Likelihood: Medium (portal updates happen periodically)
- Mitigation:
  - Log ALL selector matches (debug-level logging)
  - Implement monitoring alert for zero matches (indicates structure change)
  - Create manual review queue for failed extractions
  - Fallback to raw HTML preserves data integrity
- Detection: `len(matched_elements) == 0` triggers elevated logging

**Risk 2: Image Download Failures**
- Impact: Some images not stored as base64, stored as URLs instead
- Likelihood: Medium (network issues, CDN timeouts)
- Mitigation:
  - Implement 2 retries with exponential backoff (1s, 2s)
  - Store URL reference if download fails after retries
  - Log each image download failure with error code
  - Alert if 10%+ of images fail on any given day
  - Don't block text extraction if image downloads fail (graceful degradation)

**Risk 3: Malformed or Unexpected HTML**
- Impact: Parser crashes or unexpected tag filtering
- Likelihood: Low (using permissive parser)
- Mitigation:
  - Use BeautifulSoup with `html.parser` backend (permissive, no external dependencies)
  - Wrap extraction in try-except, fallback to plain text on exception
  - Log full stack trace and raw HTML for analysis
  - Test with real ProTradingSkills page samples

**Risk 4: Spanish Date Parsing Fails**
- Impact: Publication date not extracted, NULL in database
- Likelihood: Low-Medium (format variations, encoding issues)
- Mitigation:
  - Store original date string in image metadata as fallback
  - Log parse failure with original date string and error
  - Use robust date parsing library (python-dateutil) with fallback to regex
  - Allow NULL publication_date in database (optional field)
  - AI analyzer can infer date from report context if needed

**Risk 5: Base64 Data Makes Database Records Very Large**
- Impact: Slow queries, higher storage costs, backup complexity
- Likelihood: Low (typical images 50-500 KB, multiple images per report)
- Mitigation:
  - Compress base64 data (gzip) before storing
  - Or: Store images in separate service (S3, file system), keep only URLs
  - Monitor database size and table growth
  - Archive old reports (with images) after 2 years
  - Consider JSONB compression if PostgreSQL 16+ available

**Risk 6: Relative URLs Not Resolved Correctly**
- Impact: Image downloads fail or links broken in extracted HTML
- Likelihood: Low-Medium (common in web pages)
- Mitigation:
  - Always use `page.url` from Playwright as base URL
  - Use `urllib.parse.urljoin()` for relative URL resolution
  - Validate all URLs before download (check format, not blocked domains)
  - Log URL transformation for debugging

## Testing Strategy

**Unit Tests**

```python
# test_content_extraction.py

def test_spanish_date_parsing():
    """Test Spanish date parsing with various formats."""
    dates = [
        ("26 de noviembre de 2025 a las 15:44", datetime(2025, 11, 26, 15, 44, tzinfo=UTC)),
        ("1 de enero de 2024 a las 00:00", datetime(2024, 1, 1, 0, 0, tzinfo=UTC)),
        ("31 de diciembre de 2025 a las 23:59", datetime(2025, 12, 31, 23, 59, tzinfo=UTC)),
    ]
    for input_date, expected in dates:
        result = parse_spanish_date(input_date)
        assert result == expected

def test_tradingview_detection():
    """Test TradingView URL detection."""
    tradingview_urls = [
        "https://tradingview.com/chart/EURUSD",
        "https://www.tradingview.net/embed/chart",
        "https://tv.com/analysis",
    ]
    regular_urls = [
        "https://example.com/image.png",
        "https://broker.com/chart.png",
    ]
    for url in tradingview_urls:
        assert is_tradingview_image(url) is True
    for url in regular_urls:
        assert is_tradingview_image(url) is False

def test_semantic_html_filtering():
    """Test that non-semantic tags are removed."""
    html = '''
    <article>
      <p>Good content</p>
      <script>alert('bad')</script>
      <style>body { color: red; }</style>
      <strong>Bold text</strong>
      <div onclick="bad()">Click me</div>
    </article>
    '''
    result = extract_semantic_html(html)
    assert '<script>' not in result
    assert '<style>' not in result
    assert '<div' not in result
    assert '<p>' in result
    assert '<strong>' in result

def test_relative_url_resolution():
    """Test relative URL to absolute URL conversion."""
    base_url = "https://example.com/blog/article/"
    relative_urls = {
        "./image.png": "https://example.com/blog/article/image.png",
        "../images/chart.png": "https://example.com/blog/images/chart.png",
        "/static/logo.png": "https://example.com/static/logo.png",
    }
    for relative, expected in relative_urls.items():
        result = resolve_url(relative, base_url)
        assert result == expected

def test_allowed_tags_preservation():
    """Test that only allowed tags are preserved."""
    html = '<h1>Title</h1><p>Text</p><em>Italic</em><a href="#">Link</a><code>Code</code>'
    result = filter_semantic_tags(html)
    assert all(tag in result for tag in ['<h1>', '<p>', '<em>', '<a>'])
    assert '<code>' not in result

def test_image_base64_encoding():
    """Test image download and base64 encoding."""
    mock_image_url = "https://example.com/test-image.png"
    # Mock successful download
    result = download_and_encode_image(mock_image_url)
    assert result['content_type'] == 'image/png'
    assert len(result['base64_data']) > 0
    assert result['is_tradingview'] is False
    assert result['download_status'] == 'success'
```

**Integration Tests**

```python
# test_extraction_integration.py

async def test_full_extraction_workflow_with_real_html():
    """Test complete extraction with sample ProTradingSkills HTML."""
    # Use actual HTML snippet from ProTradingSkills
    html = load_test_html('protrading-skills-sample.html')
    extractor = ContentExtractor()

    result = await extractor.extract_from_html(
        html=html,
        report_url="https://protrading.skills/report/123",
        page_base_url="https://protrading.skills/report/123",
        correlation_id="test-123",
    )

    assert result.success is True
    assert result.author is not None
    assert result.publication_date is not None
    assert result.title is not None
    assert len(result.extracted_text) > 100
    assert len(result.extracted_images) > 0
    assert result.fallback_used is None

async def test_extraction_with_missing_author():
    """Test graceful handling when author not found."""
    html = load_test_html('protrading-skills-no-author.html')
    extractor = ContentExtractor()

    result = await extractor.extract_from_html(html, ...)

    assert result.success is True  # Still successful
    assert result.author is None  # Author is missing
    assert result.extracted_text is not None  # Content extracted
    # Check system_logs would show WARNING event

async def test_fallback_to_plain_text():
    """Test fallback when semantic HTML extraction fails."""
    html = load_test_html('malformed-html.html')
    extractor = ContentExtractor()

    result = await extractor.extract_from_html(html, ...)

    assert result.success is True
    assert result.fallback_used == 'plain_text'
    assert '<' not in result.extracted_text  # No HTML tags
    assert len(result.extracted_text) > 0

async def test_image_download_with_retry():
    """Test image download with retry logic."""
    mock_image_url = "https://example.com/image.png"

    # Mock timeout on first attempt, success on second
    with patch('requests.get') as mock_get:
        mock_get.side_effect = [
            TimeoutError(),  # First attempt fails
            MagicMock(status_code=200, content=b'...image data...')  # Retry succeeds
        ]

        result = await download_and_encode_image(mock_image_url, retries=2)

        assert result['download_status'] == 'success'
        assert mock_get.call_count == 2

async def test_database_update_with_extracted_content():
    """Test database update with extracted content."""
    report_id = "550e8400-e29b-41d4-a716-446655440000"
    extracted_text = "<h1>Title</h1><p>Content</p>"
    extracted_images = [{"url": "local://image-0", "is_tradingview": False}]

    # Mock database
    with patch('database.update_report') as mock_update:
        await save_extraction_result(report_id, extracted_text, extracted_images)

        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args.kwargs['extracted_text'] == extracted_text
        assert call_args.kwargs['extracted_images'] == extracted_images
```

**Edge Case Tests**

```python
# test_extraction_edge_cases.py

def test_empty_content_sections():
    """Test extraction with empty main content."""
    html = '<article class="pts-analysis"><div class="entry-content"></div></article>'
    result = extract_semantic_html(html)
    assert result is not None
    assert len(result) == 0 or result == ""

def test_duplicate_images():
    """Test handling of duplicate image URLs."""
    html = '''
    <article><div class="entry-content">
      <img src="https://example.com/chart.png" />
      <img src="https://example.com/chart.png" />
    </div></article>
    '''
    result = extract_images(html)
    assert len(result) == 2  # Keep duplicates

def test_missing_image_alt_text():
    """Test image without alt attribute."""
    html = '<img src="https://example.com/image.png" />'
    result = extract_images(html)
    assert result[0]['url'] == "https://example.com/image.png"
    # alt_text is None or empty, acceptable

def test_image_larger_than_size_limit():
    """Test skipping images larger than 5MB."""
    with patch('requests.get') as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            headers={'Content-Length': '6000000'}  # 6MB
        )
        result = download_and_encode_image("https://example.com/large.png")
        assert result is None or result['download_status'] == 'failed'

def test_invalid_date_format():
    """Test handling of unexpected date format."""
    invalid_dates = [
        "2025-11-26 15:44",  # ISO format, not Spanish
        "26.11.2025",        # German format
        "invalid date",      # Garbage
        "",                  # Empty
    ]
    for date_str in invalid_dates:
        result = parse_spanish_date(date_str)
        assert result is None  # Parsing fails gracefully

def test_relative_urls_in_links():
    """Test relative URL conversion in link href attributes."""
    html = '<a href="/report/123">Link</a><img src="../images/chart.png" />'
    base_url = "https://example.com/articles/trading/"
    result = resolve_all_urls(html, base_url)
    assert 'href="https://example.com/report/123"' in result
    assert 'src="https://example.com/images/chart.png"' in result
```

**Performance Tests**

```python
# test_extraction_performance.py

async def test_extraction_speed():
    """Test that extraction completes within performance targets."""
    html = load_test_html('large-protrading-report.html')
    extractor = ContentExtractor()

    start = time.time()
    result = await extractor.extract_from_html(html, ...)
    duration_ms = (time.time() - start) * 1000

    assert duration_ms < 2000  # < 2 seconds
    assert result.success is True

async def test_image_download_performance():
    """Test image downloads complete within time limit."""
    image_urls = [
        "https://example.com/image1.png",
        "https://example.com/image2.png",
        "https://example.com/image3.png",
    ]

    start = time.time()
    results = await download_images_parallel(image_urls, max_concurrent=3)
    duration_ms = (time.time() - start) * 1000

    assert duration_ms < 20000  # < 20 seconds for 3 images
    assert len(results) == 3

async def test_memory_usage_large_content():
    """Test memory usage stays reasonable with large content."""
    # Generate large HTML (10MB)
    large_html = generate_large_html(10 * 1024 * 1024)

    import psutil
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024

    extractor = ContentExtractor()
    result = await extractor.extract_from_html(large_html, ...)

    mem_after = process.memory_info().rss / 1024 / 1024
    mem_delta = mem_after - mem_before

    assert mem_delta < 200  # < 200MB peak increase
```

## Existing Code to Leverage

**HTML Parser Library Selection**
- Use BeautifulSoup 4 with `html.parser` backend (pure Python, no external dependencies like lxml)
- Permissive parser handles malformed HTML gracefully
- Provides CSS selector support via `select()` method
- Alternative: lxml if performance becomes critical (5-10x faster but adds C dependency)

**Date Parsing Library**
- Use `python-dateutil` library for robust date parsing
- Fallback to `babel` library for locale-aware month name conversion
- Simple regex pattern for Spanish date format: `r'(\d+)\s+de\s+(\w+)\s+de\s+(\d+)\s+a\s+las\s+(\d+):(\d+)'`

**Image Download Library**
- Use `httpx` with async support (compatible with FastAPI's async pattern)
- Alternative: `aiohttp` if httpx unavailable
- Configure timeouts and retry logic at library level
- Use `io.BytesIO` for in-memory image handling, no temporary files

**Base64 Encoding**
- Use Python standard library `base64` module (no external dependency)
- Validate image MIME type from response headers (Content-Type)

## Configuration & Dependencies

**Python Dependencies**

```
beautifulsoup4==4.12.x  # HTML parsing
python-dateutil==2.8.x  # Date parsing
babel==2.13.x           # Locale month name translation
httpx[http2]==0.24.x    # Async image downloading
pillow==10.x            # Image validation (optional, lightweight)
```

**Environment Variables**

```bash
# Extraction configuration
EXTRACTION_TIMEOUT_S=30           # Total extraction timeout
IMAGE_TIMEOUT_S=10               # Per-image timeout
IMAGE_MAX_SIZE_MB=5              # Max image size to download
IMAGE_RETRIES=2                  # Retry attempts for image download
MAX_PARALLEL_IMAGES=3            # Concurrent image downloads
ALLOWED_IMAGE_TYPES=image/png,image/jpeg,image/webp,image/gif

# Database (reused from email-webhook)
DATABASE_URL=postgresql://...
```

## Summary

This specification defines a robust content extraction system that intelligently extracts clean, semantic HTML from trading report pages while gracefully handling images, dates, and errors. The implementation prioritizes data integrity (no data loss), smart image handling (download regular images, preserve TradingView links), and reliable error recovery (cascading fallbacks). Integration with the existing Playwright scraper service ensures seamless operation within the trading report automation pipeline.

Key design decisions:
- Semantic HTML output optimized for Markdown conversion and AI analysis
- Cascading fallback strategy (clean HTML → plain text → raw HTML) prevents data loss
- TradingView image detection saves storage while preserving important charts
- Spanish date parsing converts to UTC timestamps for consistent storage
- Event-based logging with correlation IDs enables distributed tracing
- Graceful handling of edge cases (malformed HTML, network timeouts, missing data)
- ProTradingSkills-specific MVP allows future multi-portal support via configuration table
