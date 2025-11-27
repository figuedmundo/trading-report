# Content Extraction Module

Clean semantic HTML extraction from trading report web pages with intelligent image handling and error recovery.

## Purpose

This module extracts clean, structured content from trading report HTML pages while:
- Filtering out scripts, styles, navigation, and promotional elements
- Detecting and handling TradingView chart images intelligently
- Parsing Spanish dates to UTC timestamps
- Providing graceful fallback strategies (semantic HTML → plain text → raw HTML)
- Logging all events for monitoring and debugging

## Module Structure

```
content_extraction/
├── __init__.py              # Module exports
├── config.py                # Configuration and CSS selectors
├── models.py                # ExtractionResult dataclass
├── extractor.py             # Main ContentExtractor class
├── html_parser.py           # HTML parsing and semantic tag filtering
├── date_parser.py           # Spanish date parsing
├── image_handler.py         # Image downloading and base64 encoding
└── logging_utils.py         # Event logging integration
```

## Key Components

### ExtractionConfig
Configuration class with:
- CSS selectors for ProTradingSkills (author, date, title, content, images)
- Allowed semantic HTML tags (h1, h2, p, img, strong, em, ul, li, a)
- Filter selectors for removal (script, style, navigation, buttons)
- Image handling parameters (timeout, retries, size limits, concurrency)

### ContentExtractor
Main service class for HTML content extraction:
```python
extractor = ContentExtractor()
result = await extractor.extract_from_html(
    html=page_html,
    report_url="https://example.com/report",
    page_base_url="https://example.com/report",
    correlation_id="correlation-id",
)

# Result contains:
# - extracted_text: Clean semantic HTML or fallback
# - extracted_images: List of image metadata (JSONB)
# - author, publication_date, title: Metadata fields
# - fallback_used: None | "plain_text" | "raw_html"
# - duration_ms, images_downloaded, images_failed: Metrics
```

### ExtractionResult
Dataclass containing:
- `success: bool` - Extraction completed successfully
- `extracted_text: str` - Clean HTML or fallback text
- `extracted_images: List[Dict]` - Image metadata JSONB array
- `author, publication_date, title` - Extracted metadata
- `fallback_used` - Which fallback strategy was used
- `duration_ms, images_downloaded, images_failed` - Metrics

## Feature Highlights

### 1. Semantic HTML Extraction
Removes all non-semantic tags while preserving allowed HTML structure:
- Keeps: h1, h2, p, strong, em, ul, li, a, img
- Removes: script, style, div, span, nav, etc.
- Preserves safe attributes: href, src, alt, width, height

### 2. CSS Selector-Based Field Extraction
Extracts specific fields using ProTradingSkills selectors:
- Author: `.avatar-info-component-container .name`
- Date: `.avatar-info-component-container .text-info`
- Title: `.entry-content h2:first-of-type`
- Content: `article.pts-analysis .entry-content`
- Images: `.entry-content img`

### 3. Spanish Date Parsing
Converts Spanish date format to UTC:
- Input: "26 de noviembre de 2025 a las 15:44"
- Assumes: Europe/Madrid timezone
- Output: datetime(2025, 11, 26, 14, 44, tzinfo=UTC)

### 4. Intelligent Image Handling
- **TradingView Images**: Stored as URLs (CDN-hosted, no download)
- **Regular Images**: Downloaded, base64 encoded, with metadata
- **Parallel Downloads**: Up to 3 concurrent downloads
- **Retry Logic**: Exponential backoff for transient failures
- **Size Limits**: Max 5MB per image, min 100 bytes

### 5. Error Fallback Cascade
Never loses data:
1. Try semantic HTML extraction
2. Fall back to plain text (all HTML tags stripped)
3. Final fallback to raw HTML storage
4. Always log which fallback was used

## Usage

### Basic Extraction
```python
from src.content_extraction import extract_trading_report

result = await extract_trading_report(
    html=page_html,
    report_url="https://protrading.skills/report/123",
    page_base_url="https://protrading.skills/report/123",
    correlation_id="req-uuid",
    report_id="report-uuid",  # For logging
    db_pool=db_pool,           # For system logging
)

if result.success:
    # Update database
    db.update_report(
        report_id,
        extracted_text=result.extracted_text,
        extracted_images=result.extracted_images,
        metadata={
            "extraction_duration_ms": result.duration_ms,
            "images_downloaded": result.images_downloaded,
        }
    )
else:
    logger.error(f"Extraction failed: {result.error_message}")
```

### Custom Configuration
```python
from src.content_extraction import ContentExtractor, ExtractionConfig

config = ExtractionConfig(
    image_download_timeout_s=15,
    max_parallel_images=5,
    max_image_size_mb=10,
)

extractor = ContentExtractor(config)
result = await extractor.extract_from_html(...)
```

## Configuration

Environment variables in `.env`:
```bash
EXTRACTION_TIMEOUT_S=30           # Total extraction timeout
IMAGE_TIMEOUT_S=10                # Per-image timeout
IMAGE_MAX_SIZE_MB=5               # Max image size
IMAGE_RETRIES=2                   # Image download retries
MAX_PARALLEL_IMAGES=3             # Concurrent downloads
```

## Image Metadata Structure

Stored in PostgreSQL `reports.extracted_images` JSONB column:
```json
[
  {
    "url": "local://image-0",           // For downloaded: local reference
    "content_type": "image/png",
    "position_index": 0,
    "base64_data": "iVBORw0KGgo...",   // Only for downloaded images
    "is_tradingview": false,
    "width": 800,
    "height": 600,
    "download_status": "success"        // success | failed | tradingview_link
  },
  {
    "url": "https://tradingview.com/...", // For TradingView: full URL
    "content_type": "text/html",
    "position_index": 1,
    "is_tradingview": true,
    "download_status": "tradingview_link"
  }
]
```

## Error Handling

All errors are logged with:
- Correlation ID (for distributed tracing)
- Report ID (for audit trail)
- Event type and message
- JSONB metadata (duration, images, fallback, etc.)
- Stack traces (for errors)

Logging to PostgreSQL `system_logs` table with service_name="content_extraction".

## Testing

Run all content extraction tests:
```bash
make test-content-extraction
```

Run specific test file:
```bash
pytest tests/test_content_extraction_html.py -v
```

Test files:
- `test_content_extraction_html.py` - HTML parsing and tag filtering
- `test_content_extraction_dates.py` - Spanish date parsing
- `test_content_extraction_images.py` - Image handling
- `test_content_extractor.py` - Main extraction service
- `test_content_extraction_logging.py` - Event logging
- `test_scraper_extraction_integration.py` - Scraper integration

## Performance

- HTML parsing: < 1 second
- Image download: < 10 seconds per image
- Total extraction: < 30 seconds per report (including images)
- Memory usage: < 200MB peak

## Dependencies

- beautifulsoup4: HTML parsing
- pytz: Timezone handling
- httpx: Async image downloads
- Already in requirements.txt

## Integration Points

1. **Playwright Scraper Service**: Calls extraction after page load
2. **PostgreSQL Database**: Stores extracted content and images
3. **System Logging**: Events logged to system_logs table
4. **N8N Workflows**: Extraction status triggers next workflow steps

## Specification Reference

Full specification: `/agent-os/specs/2025-11-27-content-extraction-html-parsing/spec.md`

Key requirements:
- ProTradingSkills-specific CSS selectors
- Semantic HTML preservation with tag filtering
- Spanish date parsing (Europe/Madrid → UTC)
- TradingView image detection
- Regular image download and base64 encoding
- Graceful error fallback cascade
- Event-based system logging with correlation IDs
