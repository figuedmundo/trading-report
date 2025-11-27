# Task Breakdown: Content Extraction & HTML Parsing

## Overview
Total Tasks: 34
Total Subtasks: ~80
Estimated Duration: 4-5 dev days

This task list covers Phase 1 (MVP) content extraction for ProTradingSkills trading reports, including HTML parsing, image handling, date conversion, database integration, and system logging.

---

## Task List

### Task Group 1: Infrastructure & Database Schema
**Dependencies:** None
**Owner:** Backend Engineer
**Duration:** ~4-6 hours

#### Task 1.0: Database Schema & Migration
- [x] 1.1 Write 3-4 focused tests for database operations
  - Test JSONB field insertion with valid image metadata
  - Test NULL values handling for optional fields
  - Test constraint validation (valid_retry, data type checks)
  - **File:** `database/tests/test_content_extraction_schema.py`

- [x] 1.2 Create database migration file for extracted content fields
  - Add `extracted_text TEXT` column to reports table (stores clean semantic HTML or fallback text)
  - Add `extracted_images JSONB DEFAULT '[]'::jsonb` column to reports table (stores image metadata array)
  - Create index on `extracted_images` for performance
  - **File:** `database/migrations/005_add_content_extraction_fields.sql`
  - **Reference:** Follow pattern from `/database/migrations/002_add_indexes.sql`

- [x] 1.3 Verify migration syntax and constraints
  - Validate SQL syntax with `psql --dry-run`
  - Ensure column defaults are correct
  - Test with `make db-shell` to verify schema changes

- [x] 1.4 Update database connection tests
  - Verify reports table schema includes new columns
  - Test that migrations run successfully
  - Run ONLY the 3-4 tests written in step 1.1
  - **Command:** `cd /database && pytest tests/test_content_extraction_schema.py -v`

**Acceptance Criteria:**
- Migration file created and validated
- JSONB field properly defined with default empty array
- extracted_text column added as TEXT
- All database schema tests pass (3-4 tests)
- No constraint violations
- Existing report records unaffected

---

### Task Group 2: Core Content Extraction Module
**Dependencies:** Task Group 1
**Owner:** Backend Engineer
**Duration:** ~6-8 hours

#### Task 2.0: HTML Parsing & Semantic Tag Filtering
- [x] 2.1 Write 3-5 focused tests for HTML parsing
  - Test extraction of allowed semantic tags (h1, h2, p, strong, em, ul, li, a, img)
  - Test removal of script and style tags
  - Test preservation of tag attributes (href, src, alt, class)
  - Test handling of malformed HTML (unclosed tags)
  - Test whitespace normalization
  - **File:** `services/playwright-scraper/tests/test_content_extraction_html.py`

- [x] 2.2 Create extraction module structure
  - Create directory: `services/playwright-scraper/src/content_extraction/`
  - Create files:
    - `__init__.py` (export main classes)
    - `config.py` (CSS selectors, allowed tags, configuration)
    - `extractor.py` (main ContentExtractor class)
    - `html_parser.py` (semantic HTML filtering logic)
    - `models.py` (ExtractionResult dataclass)
  - **Reference:** Pattern from `services/email-webhook/src/` structure

- [x] 2.3 Define CSS selector configuration for ProTradingSkills
  - Create `ExtractionConfig` dataclass in `config.py`
  - Define selectors:
    - Author: `.avatar-info-component-container .name`
    - Date: `.avatar-info-component-container .text-info`
    - Title: `.entry-content h2:first-of-type`
    - Article content: `article.pts-analysis .entry-content`
    - Images: `.entry-content img`
  - Define filter-out selectors: `.return-button-container`, `.button-like`, `script`, `style`, `meta`, `link`
  - Define allowed tags: `h1`, `h2`, `p`, `img`, `strong`, `em`, `ul`, `li`, `a`
  - Add configuration for timeouts and retry logic

- [x] 2.4 Implement semantic HTML extraction logic
  - Create `extract_semantic_html()` function in `html_parser.py`
  - Use BeautifulSoup 4 with `html.parser` backend for permissive parsing
  - Extract allowed tags only, removing all other elements
  - Preserve safe attributes: `href` (a tags), `src`/`alt`/`width`/`height` (img tags)
  - Strip inline `style` attributes and `onclick`/`javascript:` protocols
  - Normalize whitespace (collapse multiple spaces, remove excessive newlines)
  - Validate HTML structure (proper nesting, closed tags)
  - Return well-formed semantic HTML string
  - **Reference:** Spec section "Content Extraction Rules"

- [x] 2.5 Implement CSS selector-based field extraction
  - Create `extract_author()`, `extract_date_string()`, `extract_title()` functions
  - Each function accepts HTML and selector, returns text or None
  - Handle missing selectors gracefully (log WARNING, return None)
  - Normalize extracted text (strip whitespace, decode HTML entities)
  - **Reference:** Spec section "Edge Cases & Handling" - Missing author or date

- [x] 2.6 Implement error fallback cascade
  - Create `extract_with_fallback()` function with graceful degradation:
    - Primary: Extract clean semantic HTML via `extract_semantic_html()`
    - Fallback 1: If semantic extraction fails (exception), strip all HTML tags → plain text
    - Fallback 2: If plain text extraction fails, return raw HTML
    - Never return None or empty string - always store something
  - Catch exceptions: `Exception` → log full traceback → apply fallback
  - Track which fallback was used in result metadata
  - Return `ExtractionResult` with fallback information

- [x] 2.7 Run HTML parsing tests only
  - Execute ONLY the 3-5 tests written in step 2.1
  - **Command:** `cd services/playwright-scraper && pytest tests/test_content_extraction_html.py -v`
  - Verify all HTML parsing and tag filtering works correctly

**Acceptance Criteria:**
- Semantic HTML parsing works for allowed tags
- Non-semantic tags (script, style, meta, link) completely removed
- Navigation/button elements removed via CSS selectors
- Malformed HTML handled gracefully by BeautifulSoup
- Fallback cascade works (semantic → plain text → raw HTML)
- All 3-5 HTML parsing tests pass
- CSS selectors correctly match ProTradingSkills structure

---

### Task Group 3: Date Parsing & Text Processing
**Dependencies:** Task Group 2
**Owner:** Backend Engineer
**Duration:** ~4-5 hours

#### Task 3.0: Spanish Date Parsing & UTC Conversion
- [x] 3.1 Write 3-4 focused tests for date parsing
  - Test parsing of Spanish date format: "26 de noviembre de 2025 a las 15:44"
  - Test all Spanish month names (enero through diciembre)
  - Test date at boundaries (1st, 28-31st of months)
  - Test graceful handling of invalid dates (log and return None)
  - **File:** `services/playwright-scraper/tests/test_content_extraction_dates.py`

- [x] 3.2 Create date parsing module
  - Create `date_parser.py` in `services/playwright-scraper/src/content_extraction/`
  - Define `SPANISH_MONTHS` dict mapping Spanish month names to numbers (1-12)
  - Define regex pattern: `r'(\d+)\s+de\s+(\w+)\s+de\s+(\d+)\s+a\s+las\s+(\d+):(\d+)'`

- [x] 3.3 Implement Spanish date parsing function
  - Create `parse_spanish_date(date_string: str) -> Optional[datetime]`
  - Extract components: day, month_name, year, hour, minute via regex
  - Map Spanish month name to number via `SPANISH_MONTHS` dict
  - Create datetime object in Europe/Madrid timezone
  - Convert to UTC timestamp (use `pytz` or `datetime.timezone.utc`)
  - Return UTC datetime object
  - **Reference:** Spec line 29-31, python-dateutil alternative if needed

- [x] 3.4 Implement error handling for date parsing
  - If regex doesn't match: log WARNING with original date string, return None
  - If month name not recognized: log WARNING, return None
  - If date is invalid (e.g., Feb 30): catch ValueError, log WARNING, return None
  - Store original date string in image metadata as fallback
  - **Reference:** Spec "Risks & Mitigations" - Risk 4

- [x] 3.5 Run date parsing tests only
  - Execute ONLY the 3-4 tests written in step 3.1
  - **Command:** `cd services/playwright-scraper && pytest tests/test_content_extraction_dates.py -v`
  - Verify Spanish date parsing and UTC conversion works correctly

**Acceptance Criteria:**
- Spanish date format "DD de MES de YYYY a las HH:MM" parses correctly
- All 12 Spanish month names recognized
- Dates converted to UTC timezone
- Invalid dates return None with WARNING log
- All 3-4 date parsing tests pass
- Timezone conversion accurate (Europe/Madrid → UTC)

---

### Task Group 4: Image Handling & Download Logic
**Dependencies:** Task Group 2
**Owner:** Backend Engineer
**Duration:** ~8-10 hours

#### Task 4.0: Image Processing & Metadata
- [x] 4.1 Write 3-6 focused tests for image handling
  - Test TradingView URL detection (tradingview.com, tradingview.net, tv.com)
  - Test regular image URL classification
  - Test image download with retry logic
  - Test base64 encoding of binary image data
  - Test image metadata structure (JSONB compliance)
  - Test handling of missing images (empty array)
  - **File:** `services/playwright-scraper/tests/test_content_extraction_images.py`

- [x] 4.2 Create image handling module
  - Create `image_handler.py` in `services/playwright-scraper/src/content_extraction/`
  - Define `TRADINGVIEW_PATTERNS` list: `["tradingview.com", "tradingview.net", "tv.com"]`
  - Define `SUPPORTED_MIME_TYPES` set: `{"image/png", "image/jpeg", "image/webp", "image/gif"}`
  - Define configuration constants:
    - `IMAGE_TIMEOUT_S = 10`
    - `IMAGE_MAX_SIZE_MB = 5`
    - `IMAGE_RETRIES = 2`
    - `MAX_PARALLEL_IMAGES = 3`

- [x] 4.3 Implement TradingView detection logic
  - Create `is_tradingview_image(url: str) -> bool` function
  - Check if URL contains any pattern from `TRADINGVIEW_PATTERNS` (case-insensitive)
  - Return True/False
  - **Reference:** Spec section "Image Detection & Classification"

- [x] 4.4 Implement URL validation and resolution
  - Create `validate_url(url: str) -> bool` function
  - Check URL starts with `http://` or `https://` (reject relative URLs initially)
  - Validate URL format (basic DNS/structure check)
  - Create `resolve_relative_url(relative_url: str, base_url: str) -> str` function
  - Use `urllib.parse.urljoin()` to convert relative URLs to absolute
  - Handle edge cases: `./`, `../`, `/`, etc.
  - **Reference:** Spec "Edge Cases & Handling" - Relative image URLs

- [x] 4.5 Implement image download with retry logic
  - Create `download_image_with_retry(url: str, timeout: int = 10, max_retries: int = 2) -> Optional[bytes]`
  - Use `httpx` for async HTTP requests (or `requests` with sync wrapper)
  - First attempt: download with specified timeout
  - On timeout/connection error: retry with exponential backoff (1s, 2s)
  - Skip retries for HTTP errors (404, 403) - log and return None
  - Check Content-Length header before download (reject > 5MB)
  - Validate response MIME type in Content-Type header
  - Return image bytes or None on failure
  - Log each attempt (success/failure with status code/error)
  - **Reference:** Spec "Image Download Workflow" and "Image Download Configuration"

- [x] 4.6 Implement base64 encoding
  - Create `encode_image_to_base64(image_bytes: bytes) -> str` function
  - Validate image is not empty (> 100 bytes minimum)
  - Encode binary data to base64 string
  - Return base64 string (no padding prefix, just the encoded data)

- [x] 4.7 Implement image metadata builder
  - Create `build_image_metadata(url: str, content_type: str, position_index: int, base64_data: Optional[str] = None, width: Optional[int] = None, height: Optional[int] = None, is_tradingview: bool = False) -> Dict`
  - Return JSONB-compatible dict with fields:
    - `url`: Original or "local://image-{index}" for downloaded
    - `content_type`: MIME type from header (e.g., "image/png")
    - `position_index`: Sequential order in article
    - `base64_data`: Base64 string (only for non-TradingView)
    - `is_tradingview`: Boolean flag
    - `width`, `height`: Optional dimensions
    - `download_status`: "success" | "failed" | "tradingview_link"
  - **Reference:** Spec "Image Metadata Structure"

- [x] 4.8 Implement parallel image downloading
  - Create `download_images_parallel(image_urls: List[str], page_base_url: str, max_concurrent: int = 3) -> List[Dict]`
  - Use `asyncio.Semaphore` to limit concurrent downloads to `max_concurrent`
  - For each URL:
    1. Resolve relative URLs to absolute using `page_base_url`
    2. Check if TradingView (don't download, set `is_tradingview=True`)
    3. Download regular images with retry logic
    4. Encode to base64 if successful
    5. Build metadata dict
    6. Replace URL with `local://image-{index}` in returned list
  - Return list of metadata dicts in same order as input
  - Handle failures gracefully (store URL reference, not base64)
  - Log each image download (success/failure with reason)

- [x] 4.9 Run image handling tests only
  - Execute ONLY the 3-6 tests written in step 4.1
  - **Command:** `cd services/playwright-scraper && pytest tests/test_content_extraction_images.py -v`
  - Verify image download, encoding, and metadata generation works

**Acceptance Criteria:**
- TradingView images correctly identified and NOT downloaded
- Regular images downloaded and encoded to base64
- Image metadata JSONB structure valid and complete
- Retry logic works (transient failures retried, permanent errors logged)
- Parallel downloads limited to max_concurrent (3)
- All image download tests pass (3-6 tests)
- Image size limits enforced (reject > 5MB)
- MIME type validation working (accept png, jpeg, webp, gif only)

---

### Task Group 5: Main Extraction Service & Integration
**Dependencies:** Task Groups 2, 3, 4
**Owner:** Backend Engineer
**Duration:** ~6-8 hours

#### Task 5.0: Core ContentExtractor Service
- [x] 5.1 Write 3-5 focused tests for main extraction service
  - Test full extraction workflow with sample HTML
  - Test extraction result includes all required fields (text, images, author, date, title)
  - Test extraction with missing author/date (should still succeed)
  - Test extraction with no images (empty array)
  - Test error fallback cascade (semantic → plain text → raw HTML)
  - **File:** `services/playwright-scraper/tests/test_content_extractor.py`

- [x] 5.2 Create main ContentExtractor class
  - Create `extractor.py` in `services/playwright-scraper/src/content_extraction/`
  - Define `ExtractionResult` dataclass with fields:
    - `success: bool` - Overall extraction success
    - `extracted_text: Optional[str]` - Clean semantic HTML or fallback
    - `extracted_images: List[Dict[str, Any]]` - Image metadata JSONB
    - `author: Optional[str]` - Extracted author name
    - `publication_date: Optional[datetime]` - Parsed and converted to UTC
    - `title: Optional[str]` - Article title
    - `fallback_used: Optional[str]` - None | "plain_text" | "raw_html"
    - `error_message: Optional[str]` - Error details if failed
    - `duration_ms: int` - Total extraction time
    - `images_downloaded: int` - Count of successfully downloaded images
    - `images_failed: int` - Count of failed image downloads
  - **Reference:** Spec "API/Interface Design" section

- [x] 5.3 Implement main extraction method
  - Create `async def extract_from_html(html: str, report_url: str, page_base_url: str, correlation_id: str) -> ExtractionResult`
  - Input validation:
    - Check html is not empty (raise ValueError if so)
    - Validate URLs with `validate_url()`
    - Generate timing context for logging
  - Execution steps (with error handling):
    1. Extract metadata: author, date, title via CSS selectors
    2. Extract semantic HTML content
    3. Find all images in article content
    4. Download/process images in parallel
    5. Replace image URLs with local references
    6. Combine results into ExtractionResult
  - Error handling: wrap each step in try-except, apply fallback logic
  - Track timing and metrics throughout
  - Return complete ExtractionResult

- [x] 5.4 Implement extraction with cascading fallbacks
  - Create `_extract_with_fallback(html: str, article_html: str) -> Tuple[str, Optional[str]]`
  - Try primary: `extract_semantic_html(article_html)` (clean semantic HTML)
  - Catch exception → Try fallback 1: Strip all HTML tags → plain text
  - Catch exception → Try fallback 2: Return raw HTML
  - Log which fallback was used (WARNING level if fallback triggered)
  - Return tuple: (extracted_text, fallback_name)
  - **Reference:** Spec "Error Handling with Fallback Cascade"

- [x] 5.5 Implement image extraction and processing
  - Create `_extract_and_process_images(article_html: str, page_base_url: str) -> Tuple[List[Dict], str]`
  - Find all `<img>` tags via CSS selector
  - Extract src, alt, width, height attributes
  - Resolve relative URLs to absolute
  - Download images in parallel via `download_images_parallel()`
  - Replace image src URLs with `local://image-{index}` in HTML
  - Return: (image_metadata_list, modified_html_with_local_refs)
  - Handle edge cases: missing images (return empty list), image download failures (store URL)

- [x] 5.6 Create integration entry point
  - Create `async def extract_trading_report(html: str, report_url: str, page_base_url: str, correlation_id: str) -> ExtractionResult`
  - This is the public API called by Playwright scraper
  - Initialize ContentExtractor with default config
  - Call `extract_from_html()` with provided parameters
  - Return ExtractionResult
  - Handle any unexpected exceptions (log, return error result)

- [x] 5.7 Run main extraction service tests only
  - Execute ONLY the 3-5 tests written in step 5.1
  - **Command:** `cd services/playwright-scraper && pytest tests/test_content_extractor.py -v`
  - Verify main extraction service and all components work together

**Acceptance Criteria:**
- ContentExtractor successfully extracts all metadata fields
- Fallback cascade works (never returns empty content)
- Image extraction and processing integrated correctly
- ExtractionResult contains all required fields
- Extraction duration tracked and reported
- All 3-5 main extraction tests pass
- Error handling graceful (no crashes, proper logging)

---

### Task Group 6: System Logging Integration
**Dependencies:** Task Group 5
**Owner:** Backend Engineer
**Duration:** ~3-4 hours

#### Task 6.0: Event Logging & Monitoring
- [x] 6.1 Write 2-3 focused tests for logging
  - Test successful extraction event logged with correct metadata
  - Test failed extraction with fallback logged as WARNING
  - Test image download failure logged with error details
  - **File:** `services/playwright-scraper/tests/test_content_extraction_logging.py`

- [x] 6.2 Implement logging wrapper
  - Create `logging_utils.py` in `services/playwright-scraper/src/content_extraction/`
  - Create `log_extraction_event()` function with parameters:
    - `correlation_id: str`
    - `report_id: str`
    - `log_level: str` (INFO, WARNING, ERROR)
    - `message: str`
    - `metadata: Dict` (extraction metrics, images found, content length, etc.)
    - Optional: `stack_trace: str` (for errors)
  - Use existing system_logging pattern from email-webhook service
  - **Reference:** Spec "System Logging Pattern" and `services/email-webhook/src/system_logging.py`

- [x] 6.3 Integrate logging into extraction flow
  - Add logging calls at key points:
    - Extraction started (DEBUG): report_id, content size
    - Author/date/title extraction (DEBUG): success/failure
    - Image downloads (DEBUG): count of images, download status
    - Extraction completed (INFO): duration_ms, images_found, content_length_bytes
    - Extraction failed (ERROR or WARNING): error message, fallback used, stack trace
  - Include metadata in each log:
    - `duration_ms`: Total extraction time
    - `images_found`: Count of <img> tags found
    - `images_downloaded`: Count successfully downloaded
    - `images_failed`: Count failed
    - `tradingview_images`: Count of TradingView images
    - `content_length_bytes`: Length of extracted_text
    - `author_extracted`: Boolean
    - `date_parsed`: Boolean
    - `fallback_used`: String or None
  - **Reference:** Spec "Database Integration" - SQL logging examples

- [x] 6.4 Run logging tests only
  - Execute ONLY the 2-3 tests written in step 6.1
  - **Command:** `cd services/playwright-scraper && pytest tests/test_content_extraction_logging.py -v`
  - Verify logging integration works correctly

**Acceptance Criteria:**
- All extraction events logged to system_logs table
- Metadata JSONB structure valid and complete
- Correlation IDs tracked throughout workflow
- Stack traces captured for errors
- All 2-3 logging tests pass
- Logging doesn't block extraction (non-blocking/async)

---

### Task Group 7: Playwright Scraper Integration
**Dependencies:** Task Groups 5, 6
**Owner:** Backend Engineer
**Duration:** ~4-5 hours

#### Task 7.0: Integration with Existing Scraper Service
- [x] 7.1 Write 3-4 focused tests for scraper integration
  - Test scraper calls extraction module after page load
  - Test database update with extracted_text and extracted_images
  - Test status transitions during extraction
  - Test extraction failure handled gracefully (no scraper crash)
  - **File:** `services/playwright-scraper/tests/test_scraper_extraction_integration.py`

- [x] 7.2 Modify Playwright scraper main service
  - File: `services/playwright-scraper/src/main.py` (or equivalent entry point)
  - Import: `from content_extraction import extract_trading_report`
  - In scraper workflow (after successful page load and authentication):
    1. Get page HTML: `html_content = page.content()`
    2. Get report URL: `report_url = report_record.report_url`
    3. Get page base URL: `page_base_url = page.url`
    4. Get correlation_id from context
    5. Call extraction: `extraction_result = await extract_trading_report(html_content, report_url, page_base_url, correlation_id)`
    6. Check result.success
    7. If success: update database with extracted_text, extracted_images, status='processing'
    8. If failure: log error, decide retry strategy, update status
  - **Reference:** Spec "Integration with Scraper Service" section

- [x] 7.3 Implement database update after extraction
  - Create `update_report_with_extracted_content()` function
  - Update reports table atomically:
    - `extracted_text` = extraction_result.extracted_text
    - `extracted_images` = extraction_result.extracted_images (as JSONB)
    - `metadata` = merge existing metadata with extraction metrics
      - Set `metadata.extraction_duration_ms`
      - Set `metadata.images_downloaded`
      - Set `metadata.images_failed`
      - Set `metadata.author_extracted`
      - Set `metadata.date_parsed`
  - Use parameterized SQL query to prevent injection
  - Handle database constraints and foreign keys
  - Log success/failure
  - **Reference:** Spec "Database Integration" - SQL Update example

- [x] 7.4 Add error handling for extraction failures
  - If extraction returns success=False:
    - Log ERROR with error_message and fallback_used
    - Update report.status (decide: mark as 'completed' with partial data, or 'failed'?)
    - Increment retry_count if should retry
    - Set error_message in reports table
  - Don't block scraper workflow on extraction errors
  - Ensure extraction failures don't crash scraper service
  - **Reference:** Spec "Error Handling & Logging" patterns

- [x] 7.5 Add extraction configuration to scraper config
  - Update scraper config file with extraction settings:
    - `EXTRACTION_TIMEOUT_S` = 30 (total timeout for full extraction)
    - `IMAGE_TIMEOUT_S` = 10 (per-image timeout)
    - `IMAGE_MAX_SIZE_MB` = 5
    - `IMAGE_RETRIES` = 2
    - `MAX_PARALLEL_IMAGES` = 3
  - Allow override via environment variables
  - **Reference:** Spec "Configuration & Dependencies"

- [x] 7.6 Run scraper integration tests only
  - Execute ONLY the 3-4 tests written in step 7.1
  - **Command:** `cd services/playwright-scraper && pytest tests/test_scraper_extraction_integration.py -v`
  - Verify extraction integrates correctly with scraper

**Acceptance Criteria:**
- Scraper calls extraction module after page load
- Extracted content stored in database correctly
- Database update includes extracted_text and extracted_images
- Status transitions valid (pending → processing → completed/failed)
- Extraction failures don't crash scraper
- Metadata properly merged into reports.metadata
- All 3-4 integration tests pass

---

### Task Group 8: Testing & Quality Assurance
**Dependencies:** Task Groups 1-7
**Owner:** QA Engineer / Backend Engineer
**Duration:** ~5-7 hours

#### Task 8.0: Comprehensive Testing & Gap Analysis
- [x] 8.1 Audit all tests written in Task Groups 1-7
  - Review 3-4 database schema tests (Task 1.1)
  - Review 3-5 HTML parsing tests (Task 2.1)
  - Review 3-4 date parsing tests (Task 3.1)
  - Review 3-6 image handling tests (Task 4.1)
  - Review 3-5 extraction service tests (Task 5.1)
  - Review 2-3 logging tests (Task 6.1)
  - Review 3-4 scraper integration tests (Task 7.1)
  - **Total existing tests: 23-31 focused tests**

- [x] 8.2 Identify critical test coverage gaps for THIS feature only
  - Analyze test coverage within content extraction scope
  - Focus on user workflows and integration points, not exhaustive coverage
  - Identify gaps in:
    - End-to-end extraction with real ProTradingSkills HTML samples
    - Fallback cascade behavior under different failure scenarios
    - Database transaction integrity (no partial updates)
    - Concurrent image downloads with multiple images
    - Large content handling (performance expectations)
  - DO NOT assess entire application test coverage
  - DO NOT write tests for non-critical edge cases (e.g., all month names, all timezones)

- [x] 8.3 Write up to 8 strategic gap-filling tests
  - Add MAXIMUM 8 new tests to cover critical integration gaps
  - Focus on end-to-end workflows and error conditions
  - Suggested tests:
    - Test full extraction with real HTML sample (file from ProTradingSkills)
    - Test extraction with all fallback scenarios (semantic fail, plain text fail, raw HTML)
    - Test concurrent extraction of multiple reports
    - Test database consistency under concurrent updates
    - Test image download with network failure and retry
    - Test extraction timeout handling
    - Test memory usage with large reports
    - Test extraction with missing critical fields (author, date, content)
  - **File:** `services/playwright-scraper/tests/test_content_extraction_e2e.py`

- [x] 8.4 Run feature-specific tests only
  - Execute ALL content extraction tests (both original + gap-filling)
  - **Command:**
    ```bash
    cd services/playwright-scraper && pytest \
      tests/test_content_extraction_html.py \
      tests/test_content_extraction_dates.py \
      tests/test_content_extraction_images.py \
      tests/test_content_extractor.py \
      tests/test_content_extraction_logging.py \
      tests/test_scraper_extraction_integration.py \
      tests/test_content_extraction_e2e.py \
      -v
    ```
  - Expected: 31-39 tests passing
  - Verify critical workflows work end-to-end
  - DO NOT run entire application test suite at this stage

- [x] 8.5 Test with real ProTradingSkills sample HTML
  - Obtain sample HTML from actual ProTradingSkills report
  - Save to: `services/playwright-scraper/tests/fixtures/protrading-skills-sample.html`
  - Create test: `test_extraction_with_real_protrading_report()`
  - Verify extraction works correctly with real page structure
  - Check metadata accuracy (author, date, title)
  - Verify images detected and categorized (TradingView vs regular)

- [x] 8.6 Validate database integrity
  - Verify no constraint violations (FK, NOT NULL, data type checks)
  - Verify JSONB field structure matches schema
  - Verify metadata merge works correctly
  - Verify transaction rollback on error
  - Run: `make db-shell` and spot-check records

**Acceptance Criteria:**
- All feature-specific tests pass (31-39 tests total)
- No more than 8 additional tests added for gap coverage
- Critical user workflows covered (extraction with all fallbacks)
- Real ProTradingSkills HTML sample tested successfully
- Database integrity verified (no constraint violations)
- Performance targets met (<30s per report including images)

---

### Task Group 9: Documentation & Deployment Readiness
**Dependencies:** Task Groups 1-8
**Owner:** Backend Engineer / DevOps
**Duration:** ~3-4 hours

#### Task 9.0: Documentation & Code Cleanup
- [x] 9.1 Add inline code documentation
  - Add docstrings to all public methods in content_extraction module
  - Document parameters and return types (using type hints)
  - Explain complex logic (CSS selectors, fallback cascade, image parallel downloads)
  - Include references to spec sections where relevant
  - **Reference:** `agent-os/standards/global/commenting.md` patterns

- [x] 9.2 Create module README
  - File: `services/playwright-scraper/src/content_extraction/README.md`
  - Document module purpose and architecture
  - List key functions and their responsibilities
  - Provide usage examples
  - Link to main spec: `agent-os/specs/2025-11-27-content-extraction-html-parsing/spec.md`

- [x] 9.3 Add configuration documentation
  - File: `services/playwright-scraper/.env.example`
  - Add new env vars for extraction:
    - `EXTRACTION_TIMEOUT_S=30`
    - `IMAGE_TIMEOUT_S=10`
    - `IMAGE_MAX_SIZE_MB=5`
    - `IMAGE_RETRIES=2`
    - `MAX_PARALLEL_IMAGES=3`
  - Document each setting

- [x] 9.4 Update Makefile for testing
  - Add target: `test-content-extraction`
    ```makefile
    test-content-extraction:
        cd services/playwright-scraper && pytest tests/test_content_extraction_*.py -v
    ```
  - Add target: `test-extraction-e2e`
    ```makefile
    test-extraction-e2e:
        cd services/playwright-scraper && pytest tests/test_content_extraction_e2e.py -v
    ```

- [x] 9.5 Verify migration deployment readiness
  - Ensure migration file has proper version timestamp
  - Verify migration is idempotent (can run multiple times safely)
  - Test rollback strategy (if needed)
  - Document migration purpose in comments

- [x] 9.6 Create quick-start guide for extraction feature
  - File: `agent-os/specs/2025-11-27-content-extraction-html-parsing/IMPLEMENTATION.md`
  - Document key components and responsibilities
  - Explain integration with scraper service
  - Provide troubleshooting tips (common failure modes)
  - Include performance benchmarks achieved

**Acceptance Criteria:**
- All public functions have docstrings
- Module README created and complete
- Configuration documented (.env.example updated)
- Makefile targets added for testing
- Migration deployment-ready
- Quick-start implementation guide created

---

## Summary & Execution Order

### Recommended Implementation Sequence
1. **Task Group 1**: Database Schema (Foundation - 4-6h)
2. **Task Groups 2-4**: Core Modules (HTML, Date, Image - 18-23h in parallel)
3. **Task Group 5**: Main Service (Integration hub - 6-8h)
4. **Task Group 6**: Logging (Observability - 3-4h)
5. **Task Group 7**: Scraper Integration (System integration - 4-5h)
6. **Task Group 8**: Testing & QA (Validation - 5-7h)
7. **Task Group 9**: Documentation (Finalization - 3-4h)

**Total Estimated Duration**: 4-5 development days (44-57 hours of focused work)

### Critical Path Dependencies
- Task 1 (Schema) → Task 7 (Integration)
- Task 2-4 (Core modules) → Task 5 (Main service)
- Task 5 (Main service) → Task 6 (Logging)
- Task 6 (Logging) → Task 7 (Scraper integration)
- Task 7 (Scraper integration) → Task 8 (Testing)

### Parallel Work Opportunities
- Tasks 2, 3, 4 can be developed in parallel once Task 1 is complete
- Within Task 2-4, different engineers can work on each module
- Task 6 (Logging) can be started once Task 5 core structure is defined

---

## Key Success Metrics

By end of implementation:
- [x] All 9 task groups completed
- [x] 31-39 feature-specific tests passing
- [x] Extraction accuracy: 100% author/date/title, 95%+ content, 100% image detection
- [x] Performance: <30s per report including images
- [x] Zero data loss: Fallback cascade always succeeds
- [x] Database: JSONB schema valid, no constraint violations
- [x] Logging: All events tracked with correlation IDs
- [x] Integration: Seamless with existing Playwright scraper
- [x] Documentation: Complete and deployment-ready

---

## Reference Files & Standards

**Existing Code to Reference:**
- Database patterns: `/database/migrations/001_initial_schema.sql`, `/database/migrations/002_add_indexes.sql`
- System logging: `services/email-webhook/src/system_logging.py`
- Database operations: `services/email-webhook/src/database.py`
- Models/validation: `services/email-webhook/src/models.py`

**Standards to Follow:**
- Backend API patterns: `agent-os/standards/backend/api.md`
- Database models: `agent-os/standards/backend/models.md`
- Global coding style: `agent-os/standards/global/coding-style.md`
- Error handling: `agent-os/standards/global/error-handling.md`
- Test writing: `agent-os/standards/testing/test-writing.md`
- Validation: `agent-os/standards/global/validation.md`

**Spec Documentation:**
- Full specification: `agent-os/specs/2025-11-27-content-extraction-html-parsing/spec.md`
- Requirements: `agent-os/specs/2025-11-27-content-extraction-html-parsing/planning/requirements.md`

---

## Notes for Implementation

### Technology Stack Confirmed
- **HTML Parser**: BeautifulSoup 4 with `html.parser` backend (permissive, no external deps)
- **Date Parsing**: `python-dateutil` or simple regex + `babel` for Spanish month names
- **Image Downloading**: `httpx` with async support (or `requests` sync wrapper)
- **Base64 Encoding**: Python standard library `base64` module
- **Database**: PostgreSQL with SQLAlchemy (existing patterns)
- **Logging**: Event-based to system_logs table (existing pattern)

### Important Constraints
- MVP scope: ProTradingSkills only with hardcoded CSS selectors
- No promotional content filtering (AI analysis handles this)
- TradingView images NOT downloaded (save space, use CDN)
- Spanish date parsing only (future phases can extend)
- Graceful degradation on errors (always store something)

### Common Pitfalls to Avoid
- Don't implement keyword-based promotional filtering (AI's job)
- Don't download TradingView images (defeats the purpose)
- Don't lose data on extraction failures (use fallback cascade)
- Don't block scraper service on extraction errors (graceful degradation)
- Don't make image download synchronous (use parallel/async)

---

**Last Updated**: November 27, 2025
**Specification Version**: 1.0
