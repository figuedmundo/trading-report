# Task Breakdown: Unified Notification Service

## Overview

Total Tasks: 47 sub-tasks across 5 phases

**Purpose**: Consolidate email and Telegram notification delivery into a single, extensible multi-channel notification service that replaces two separate services with a unified factory-based architecture.

**Key Deliverables**:
- Single FastAPI service handling all notification channels
- Database-backed retry mechanism with exponential backoff
- Per-channel rate limiting via token bucket algorithm
- Complete audit trail with append-only delivery logs
- Configuration-driven channel registration supporting future extensibility

## Task List

### Phase 1: Core Service Structure

#### Task 1.0: Database Migrations for Notification Service
**Dependencies:** None

- [x] 1.1 Write 3-5 focused tests for database migrations
  - Test notifications_delivery_log table creation and indexes
  - Test channel_configurations table creation with unique constraints
  - Test notifications table updates (new columns if any)
  - Run ONLY these 3-5 tests after implementation

- [x] 1.2 Create migration: notifications_delivery_log table
  - File: `database/migrations/007_create_notifications_delivery_log.sql`
  - Columns: id, notification_id (FK), attempt_number, channel, recipient, status, sent_at, latency_ms, external_id, error_code, error_message, retry_after_seconds, metadata, created_at
  - Indexes: idx_delivery_log_notification_id, idx_delivery_log_channel, idx_delivery_log_created_at (DESC), idx_delivery_log_status
  - Constraints: ON DELETE CASCADE for notification_id
  - Append-only design: INSERT only, no UPDATE allowed after creation

- [x] 1.3 Create migration: channel_configurations table
  - File: `database/migrations/008_create_channel_configurations.sql`
  - Columns: id, channel_name, is_enabled, setting_key, setting_value, description, created_at, updated_at
  - Unique constraint: (channel_name, setting_key)
  - Insert sample data for email and telegram configuration rows:
    - email: rate_limit_per_hour=100, smtp_timeout_seconds=10, max_retries=5
    - telegram: rate_limit_per_minute=30, api_timeout_seconds=5, max_retries=5

- [x] 1.4 Update notification_channel enum type if needed
  - Verify enum includes: telegram, email (already present)
  - Extend enum for future: sms, slack, discord, webhook (comment as Phase 2+)
  - File: Update in same migration or separate `008_extend_enums.sql`

- [x] 1.5 Ensure database migration tests pass
  - Run ONLY the 3-5 tests written in 1.1
  - Verify migrations run successfully with `make db-shell` inspection
  - Confirm indexes created correctly: `\di` in psql
  - Verify constraints working: insert test data and verify unique constraint violations

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- notifications_delivery_log table exists with correct schema and indexes
- channel_configurations table exists with correct schema and unique constraint
- Sample configuration data inserted for email and telegram
- Migrations are reversible and can rollback cleanly

---

#### Task 2.0: Service Structure, Configuration & Initialization
**Dependencies:** Task 1.0

- [x] 2.1 Write 3-5 focused tests for service configuration
  - Test Config class loads environment variables correctly
  - Test validate_config() returns False when required vars missing
  - Test database connection pool initialization
  - Test lifespan context manager startup/shutdown
  - Run ONLY these 3-5 tests after implementation

- [x] 2.2 Create FastAPI application skeleton
  - File: `services/notification-service/src/main.py`
  - Follow pattern from services/ai-analyzer/src/main.py
  - Use asynccontextmanager for lifespan management
  - Initialize database pool on startup
  - Close database pool on shutdown
  - Add CORS middleware for service-to-service communication
  - Include router.include_router(router) for API routes (implement in Task 2.5)

- [x] 2.3 Implement Config class and configuration management
  - File: `services/notification-service/src/config.py`
  - Follow pattern from services/ai-analyzer/src/config.py
  - Load environment variables: SERVICE_PORT, LOG_LEVEL, DATABASE_URL, DATABASE_POOL_MIN, DATABASE_POOL_MAX
  - Load SMTP secrets: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL
  - Load Telegram secret: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (optional, can override per request)
  - Load optional: CORRELATION_ID_HEADER, LOG_LEVEL
  - Implement validate_config() function checking critical fields
  - Properties for each config value with type hints

- [x] 2.4 Create database connection pool and async context manager
  - File: `services/notification-service/src/db/connection.py`
  - Follow pattern from services/ai-analyzer/src/db/connection.py
  - Use asyncpg.create_pool() with min_size=DB_POOL_MIN, max_size=DB_POOL_MAX
  - Implement init_db_pool() called during startup
  - Implement close_db_pool() called during shutdown
  - Implement async context manager for transaction management: async with pool.acquire() as conn
  - Implement retry logic with exponential backoff for connection failures
  - Include health check method: async def check_db_health() -> bool

- [x] 2.5 Create base exception hierarchy
  - File: `services/notification-service/src/utils/exceptions.py`
  - Follow pattern from services/ai-analyzer/src/utils/exceptions.py
  - Base exception: NotificationError(Exception) with message and error_type
  - Child exceptions: ChannelError, TemplateError, ConfigurationError, RateLimitError, ValidationError
  - Each child exception with clear error_type string for API response mapping
  - Include __str__() method for logging and user-facing messages

- [x] 2.6 Create logging module
  - File: `services/notification-service/src/utils/logger.py`
  - Follow pattern from services/ai-analyzer/src/utils/logger.py
  - Function: get_logger(name) returning Python logger with structured format
  - Include timestamp, log level, service name in output
  - Support LOG_LEVEL environment variable for runtime configuration
  - Implement extra parameter usage for context fields: logger.info("msg", extra={"notification_id": id})

- [x] 2.7 Create Pydantic request/response models
  - File: `services/notification-service/src/models.py`
  - Follow pattern from services/ai-analyzer/src/models.py
  - Request models:
    - NotificationRequest: analysis_id, report_id, channels (List[str]), recipients (Dict[str, str]), message_type (str default 'summary')
    - NotificationBatchRequest: notifications (List[NotificationRequest])
  - Response models:
    - NotificationSuccessResponse: request_id, status, notification_ids (List[str]), timestamp, channels_created (Dict[str, str]), duration_ms
    - NotificationErrorResponse: request_id, error, error_code, affected_channels (List[str]), timestamp
    - DeliveryStatusResponse: notification_id, analysis_id, channel, recipient (masked), status, sent_at (optional), latency_ms (optional), external_id (optional), retry_count, created_at
    - HealthCheckResponse: status, service, version, timestamp, channels (Dict[str, str]), database (str)
    - ChannelStatusResponse: channels (List[Dict with name, enabled, rate_limit, tokens_available])
  - Include field_validator for channels list (valid channels: email, telegram, sms, slack, discord)
  - Include validation for recipients dict (non-empty, matching channel list)

- [x] 2.8 Create health check endpoint
  - File: `services/notification-service/src/api/routes.py` (new file)
  - Endpoint: GET /health
  - Check database connection pool health: await check_db_health()
  - Check each enabled channel configuration validity
  - Return 200 OK if all critical components healthy
  - Return 503 Service Unavailable if database unreachable
  - Response: HealthCheckResponse with channels and database status
  - Include timestamp and service version

- [x] 2.9 Ensure configuration and initialization tests pass
  - Run ONLY the 3-5 tests written in 2.1
  - Verify FastAPI app starts without errors
  - Verify config loads from environment correctly
  - Verify database pool initializes and closes cleanly
  - Run in Docker: verify service starts with `docker-compose up notification-service`

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- FastAPI app with lifespan management created
- Config class loads and validates environment variables correctly
- Database connection pool initializes and manages connections
- Exception hierarchy with proper error types for routing
- Logging module configured with structured output
- Pydantic models validate request/response data
- Health check endpoint responds with service status
- All imports work and no circular dependencies

---

### Phase 2: Channel Implementations

#### Task 3.0: Base Channel Abstract Class & Factory Pattern
**Dependencies:** Task 2.0

- [x] 3.1 Write 3-5 focused tests for channel architecture
  - Test Channel abstract class cannot be instantiated directly
  - Test ChannelFactory loads enabled channels from database
  - Test Channel.validate_config() requires implementation by subclasses
  - Test ChannelFactory instantiates EmailChannel and TelegramChannel correctly
  - Run ONLY these 3-5 tests after implementation

- [x] 3.2 Create base Channel abstract class
  - File: `services/notification-service/src/channels/base.py`
  - Class: Channel(ABC) with abstract methods:
    - async def send(message: str, recipient: str) -> Dict[str, Any]
    - def validate_recipient(recipient: str) -> bool
    - def validate_config() -> bool
  - Non-abstract method: get_channel_status() -> Dict[str, Any]
  - Non-abstract method: async def check_rate_limit() -> bool
  - Constructor: __init__(name: str, config: Dict[str, Any])
  - Instance variables: self.name, self.config, self.rate_limiter
  - Return format for send(): {success: bool, external_id: str (optional), latency_ms: int, error_code: str (optional), error_message: str (optional)}

- [x] 3.3 Create ChannelFactory for dynamic channel instantiation
  - File: `services/notification-service/src/channels/factory.py`
  - Class: ChannelFactory with async methods
  - async def load_channels_from_config() -> Dict[str, Channel]
    - Query channel_configurations table for all enabled channels
    - For each enabled channel: instantiate corresponding Channel subclass
    - Return dict mapping channel_name -> Channel instance
  - async def get_channel(channel_name: str) -> Channel or None
    - Return loaded channel instance or None if not enabled
  - async def reload_channels() -> None
    - Reload channels from database (supports runtime enable/disable)
  - Static method: _instantiate_channel(channel_name: str, config: Dict) -> Channel
    - Map channel_name to class: email -> EmailChannel, telegram -> TelegramChannel
    - Raise ConfigurationError if channel not found or config invalid

- [x] 3.4 Create channel module structure
  - File: `services/notification-service/src/channels/__init__.py`
  - Export: Channel, ChannelFactory, EmailChannel, TelegramChannel
  - File: `services/notification-service/src/channels/email.py` (placeholder for 3.5)
  - File: `services/notification-service/src/channels/telegram.py` (placeholder for 3.6)

- [x] 3.5 Ensure channel architecture tests pass
  - Run ONLY the 3-5 tests written in 3.1
  - Verify Channel abstract class properly prevents instantiation
  - Verify ChannelFactory loads channels from database mock
  - Verify error handling when channel type not found
  - Verify rate_limiter assignment in channel instances

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- Base Channel abstract class with required abstract methods
- ChannelFactory loads channels from database configuration
- Channel subclasses will implement send(), validate_recipient(), validate_config()
- Factory pattern allows adding new channels without code changes

---

#### Task 4.0: Email Channel Implementation with SMTP
**Dependencies:** Task 3.0

- [x] 4.1 Write 3-5 focused tests for EmailChannel
  - Test validate_recipient() correctly validates email format (valid, invalid, edge cases)
  - Test validate_config() checks for SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
  - Test send() success with mocked SMTP (return success=True, external_id, latency_ms)
  - Test send() failure with invalid email (return success=False, error_code='INVALID_EMAIL')
  - Run ONLY these 3-5 tests after implementation

- [x] 4.2 Implement EmailChannel class
  - File: `services/notification-service/src/channels/email.py`
  - Class: EmailChannel(Channel)
  - async def send(message: str, recipient: str) -> Dict[str, Any]:
    - Validate recipient email format first
    - Render HTML and plain text versions (TODO: template rendering in Task 5.1)
    - Send via SMTP with timeout=10 seconds (from config)
    - Track latency_ms
    - Catch SMTPException and return failure response with error_code and error_message
    - Return success response with RFC 5322 Message-ID as external_id
  - def validate_recipient(recipient: str) -> bool:
    - Use regex pattern: r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
  - def validate_config() -> bool:
    - Check required keys: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
    - Check SMTP_PORT is valid integer

- [x] 4.3 Create SMTP connection handler
  - File: `services/notification-service/src/channels/smtp_client.py`
  - Class: SMTPClient with async methods
  - async def __aenter__() and async def __aexit__() for async context manager
  - async def send_message(to_addr: str, subject: str, html_body: str, text_body: str, timeout: int) -> str
    - Use aiosmtplib for async SMTP connection
    - Create MIMEMultipart with HTML and plain text parts
    - Set Message-ID header automatically (RFC 5322)
    - Return Message-ID string
    - Raise SMTPException with smtp_code for error handling
  - async def test_connection() -> bool
    - Validate SMTP credentials at startup

- [x] 4.4 Add email template rendering (basic, enhanced in Task 5.1)
  - File: `services/notification-service/src/channels/email.py`
  - In send() method: call template renderer (placeholder for now)
  - TODO: full template rendering in Task 5.1 (Jinja2 template system)
  - For now: accept pre-rendered message from caller (NotificationService will render)

- [x] 4.5 Ensure email channel tests pass
  - Run ONLY the 3-5 tests written in 4.1
  - Verify validate_recipient() works for valid/invalid emails
  - Verify SMTP config validation
  - Verify mocked SMTP send returns correct response structure
  - Verify error handling and exception mapping

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- EmailChannel implements Channel interface
- Email format validation working
- SMTP configuration validation
- Async SMTP client for sending emails with timeout
- Proper error handling with error_code mapping (INVALID_EMAIL, SMTP_ERROR, TIMEOUT, etc.)

---

#### Task 5.0: Telegram Channel Implementation with Bot API
**Dependencies:** Task 3.0

- [x] 5.1 Write 3-5 focused tests for TelegramChannel
  - Test validate_recipient() correctly validates numeric chat IDs (valid, invalid)
  - Test validate_config() checks for TELEGRAM_BOT_TOKEN
  - Test send() success with mocked Telegram API (return success=True, external_id, latency_ms)
  - Test send() failure with invalid chat ID (return success=False, error_code='INVALID_CHAT_ID')
  - Test message splitting for >4096 characters
  - Run ONLY these 3-5 tests after implementation

- [x] 5.2 Implement TelegramChannel class
  - File: `services/notification-service/src/channels/telegram.py`
  - Class: TelegramChannel(Channel)
  - async def send(message: str, recipient: str) -> Dict[str, Any]:
    - Validate recipient is numeric chat ID
    - Split message if exceeds 4096 characters: _split_message(message, 4096)
    - Send each chunk via Telegram API with parse_mode='Markdown'
    - Track total latency_ms for all chunks
    - Return success with external_id (pipe-separated message IDs if split)
    - Catch TelegramError and return failure response with error_code and error_message
  - def validate_recipient(recipient: str) -> bool:
    - Try parsing as integer: int(recipient), return True if successful
  - def validate_config() -> bool:
    - Check TELEGRAM_BOT_TOKEN is present and non-empty

- [x] 5.3 Create Telegram API client
  - File: `services/notification-service/src/channels/telegram_client.py`
  - Class: TelegramClient with async methods
  - async def send_message(chat_id: str, text: str, timeout: int) -> str
    - Use aiohttp or httpx for async HTTP
    - Call Telegram Bot API: sendMessage endpoint
    - Include parse_mode='Markdown'
    - Return message_id from response
    - Raise TelegramError with error_code for error handling
  - async def test_connection() -> bool
    - Call getMe endpoint to validate bot token

- [x] 5.4 Implement message splitting logic
  - File: `services/notification-service/src/channels/telegram.py`
  - Method: _split_message(message: str, max_length: int) -> List[str]
    - Split on paragraph boundaries if possible (double newline)
    - Fallback to word boundaries (space)
    - Don't split in middle of markdown formatting
    - Return list of message chunks, each <= max_length

- [x] 5.5 Ensure telegram channel tests pass
  - Run ONLY the 3-5 tests written in 5.1
  - Verify validate_recipient() works for numeric and non-numeric inputs
  - Verify bot token validation
  - Verify mocked Telegram API send returns correct response
  - Verify message splitting logic

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- TelegramChannel implements Channel interface
- Chat ID validation (numeric format)
- Telegram bot token configuration validation
- Async Telegram API client for sending messages with timeout
- Message splitting for 4096 character limit
- Proper error handling with error_code mapping

---

#### Task 6.0: Jinja2 Template System
**Dependencies:** Task 2.0, Task 4.0, Task 5.0

- [x] 6.1 Write 3-5 focused tests for template rendering
  - Test template loader finds email/summary.jinja2 and telegram/summary.jinja2
  - Test template validation fails for missing required templates at startup
  - Test render() with valid template variables returns rendered string
  - Test filter functions: title, round, datetimeformat
  - Run ONLY these 3-5 tests after implementation

- [x] 6.2 Create template directory structure
  - Directory: `services/notification-service/templates/`
  - Subdirectories: email/, telegram/, shared/
  - Placeholder templates (implement actual content in 6.4):
    - templates/email/summary.jinja2
    - templates/email/alert.jinja2
    - templates/email/detailed_report.jinja2
    - templates/telegram/summary.jinja2
    - templates/telegram/alert.jinja2
    - templates/telegram/detailed_report.jinja2
    - templates/shared/macros.jinja2

- [x] 6.3 Create template rendering engine
  - File: `services/notification-service/src/templates/engine.py`
  - Class: TemplateEngine with initialization
  - __init__(): Initialize Jinja2 FileSystemLoader pointing to templates directory
  - Add filters: title, round (with precision), datetimeformat (custom date formatter)
  - async def render(template_path: str, context: Dict[str, Any]) -> str
    - Load template_path from env
    - Render with context variables
    - Raise TemplateError if template not found or rendering fails
  - def validate_templates_at_startup() -> bool
    - Check required templates exist for each enabled channel
    - Log CRITICAL error and raise ConfigurationError if missing
  - def get_template_variables_schema() -> Dict
    - Return expected schema for template variables (documentation)

- [x] 6.4 Create email template (email/summary.jinja2)
  - HTML email template with:
    - Title: {{ report_title }}
    - Metrics row: sentiment, confidence_score, win_rate (if present)
    - Summary paragraph: {{ summary }}
    - Trading Signals section with loop over trading_signals:
      - Signal action, symbol, entry_price, target_price, confidence_score
      - CSS classes for sentiment styling (.bullish, .bearish, .neutral)
    - Footer with report link, generated timestamp, AI provider
    - Inline CSS for styling (no external stylesheets)
    - Fallback to plain text if rendering fails (note in acceptance criteria)

- [x] 6.5 Create telegram template (telegram/summary.jinja2)
  - Markdown formatted text message with:
    - Title emoji: 📊 *{{ report_title }}*
    - Metrics: Sentiment, Win Rate, etc.
    - Summary text: {{ summary }}
    - Trading signals section with bullet points
    - Link to report: [Full Report]({{ report_url }})
    - Footer with AI provider info
    - Respect 4096 character limit (will be split by channel)

- [x] 6.6 Create template variables builder in NotificationService
  - File: `services/notification-service/src/services/notification_service.py`
  - Method: async def _build_template_variables(analysis_id: str) -> Dict[str, Any]
    - Query analyses table for analysis data
    - Extract: report_title, summary, trading_signals, sentiment, confidence_score, win_rate, profit_loss
    - Build template variables dict with all required fields
    - Return dict ready for Jinja2 rendering

- [x] 6.7 Ensure template system tests pass
  - Run ONLY the 3-5 tests written in 6.1
  - Verify template loader finds all templates
  - Verify startup validation catches missing templates
  - Verify render() returns non-empty string with expected variables substituted
  - Verify Jinja2 filters work correctly

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- Jinja2 template system integrated with filesystem loader
- Template directory structure created with all required templates
- Template validation at service startup (fail fast)
- Custom filters (title, round, datetimeformat) working
- Email and Telegram templates created with proper formatting
- Template variables schema documented in code

---

#### Task 7.0: Token Bucket Rate Limiter
**Dependencies:** Task 2.0

- [x] 7.1 Write 3-5 focused tests for rate limiting
  - Test try_consume(1) succeeds when tokens available
  - Test try_consume(n) fails when insufficient tokens
  - Test token refill over time (mock time advancement)
  - Test get_retry_after_seconds() calculates correct wait time
  - Run ONLY these 3-5 tests after implementation

- [x] 7.2 Implement TokenBucket class
  - File: `services/notification-service/src/utils/rate_limiter.py`
  - Class: TokenBucket
  - __init__(capacity: int, refill_rate: float)
    - capacity: max tokens (e.g., 100 for 100 emails/hour)
    - refill_rate: tokens per second (e.g., 100/3600 for 100/hour)
    - self.tokens = capacity (start full)
    - self.last_refill = time.time()
  - async def try_consume(tokens: int = 1) -> bool
    - Call _refill() to update token count
    - If self.tokens >= tokens: decrement and return True
    - Else: return False (rate limited)
  - async def _refill() -> None
    - Calculate elapsed time since last refill
    - Add elapsed * refill_rate tokens
    - Cap at capacity
    - Update last_refill timestamp
  - def get_retry_after_seconds() -> int
    - If tokens >= 1: return 0
    - Calculate seconds until next token available
    - Return ceil(needed_tokens / refill_rate)

- [x] 7.3 Initialize rate limiters for each channel
  - File: `services/notification-service/src/channels/factory.py`
  - In _instantiate_channel(): set channel.rate_limiter = TokenBucket(...)
  - Email: capacity=100, refill_rate=100/3600 (100 per hour)
  - Telegram: capacity=30, refill_rate=30/60 (30 per minute)
  - Load rate limits from channel_configurations table if available
  - Fallback to defaults if not in database

- [x] 7.4 Ensure rate limiter tests pass
  - Run ONLY the 3-5 tests written in 7.1
  - Verify token consumption and depletion
  - Verify token refill calculation
  - Verify retry_after_seconds calculation

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- TokenBucket algorithm correctly implements token consumption and refill
- Rate limiters initialized per channel with correct limits
- Retry after calculation accurate for rate limit responses
- Per-channel independent rate limiting (email and telegram don't share tokens)

---

#### Task 8.0: Notification Service Orchestration Layer
**Dependencies:** Task 3.0, Task 4.0, Task 5.0, Task 6.0, Task 7.0

- [x] 8.1 Write 3-5 focused tests for notification service
  - Test send() creates notification records in database
  - Test send() calls template renderer and gets rendered message
  - Test send() calls each enabled channel's send() method
  - Test send() handles rate limit errors and returns 429
  - Run ONLY these 3-5 tests after implementation

- [x] 8.2 Implement NotificationService class
  - File: `services/notification-service/src/services/notification_service.py`
  - Class: NotificationService with dependency injection
  - __init__(db_pool, channel_factory, template_engine, logger)
  - async def send(request: NotificationRequest) -> Dict[str, Any]
    - Validate request (channels, recipients match)
    - Create notification records in DB for each channel (status='pending')
    - For each channel: render template + send via channel
    - Update notification status (sent/failed/retrying)
    - Insert delivery log entry
    - Return response with notification_ids and summary
  - async def _render_message(channel: str, message_type: str, context: Dict) -> str
    - Build template path: f"templates/{channel}/{message_type}.jinja2"
    - Call template_engine.render(path, context)
  - async def _send_via_channel(notification_id: str, channel: Channel, message: str, recipient: str) -> bool
    - Check rate limit: await channel.check_rate_limit()
    - If rate limited: increment retry_count, log warning, return False (will retry)
    - Call channel.send(message, recipient)
    - Handle success/failure responses
    - Update notifications table with status, sent_at, message_id, error_message
    - Insert notifications_delivery_log entry
    - Return success boolean
  - async def _build_template_context(analysis_id: str) -> Dict
    - Query analyses table for analysis data
    - Build context with all template variables
    - Query reports/symbols/signals to populate full context

- [x] 8.3 Create notification repository layer
  - File: `services/notification-service/src/db/notifications_repository.py`
  - Class: NotificationsRepository with database pool
  - async def create_notification(analysis_id: str, channel: str, recipient: str, message_type: str) -> str
    - Insert into notifications table with status='pending'
    - Return notification_id
  - async def update_notification_status(notification_id: str, status: str, sent_at: datetime, message_id: str, error_message: str, retry_count: int)
    - Update notifications table
    - Call updated_at trigger to auto-update timestamp
  - async def get_notification(notification_id: str) -> Dict
    - Query notifications table
  - async def insert_delivery_log(notification_id: str, attempt_number: int, channel: str, recipient: str, status: str, sent_at: datetime, latency_ms: int, external_id: str, error_code: str, error_message: str, retry_after_seconds: int)
    - Insert into notifications_delivery_log (append-only)

- [x] 8.4 Integrate NotificationService into main.py lifespan
  - File: `services/notification-service/src/main.py`
  - In lifespan startup:
    - Initialize ChannelFactory
    - await channel_factory.load_channels_from_config()
    - Initialize TemplateEngine
    - await template_engine.validate_templates_at_startup()
    - Initialize NotificationService with dependencies
    - Store in app.state for route handlers to access

- [x] 8.5 Ensure notification service tests pass
  - Run ONLY the 3-5 tests written in 8.1
  - Verify notification records created in database
  - Verify template rendering called correctly
  - Verify channel send() called for each channel
  - Verify rate limit handling and retry_count increment

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- NotificationService orchestrates message rendering and channel delivery
- Notification records created and updated in database
- Delivery logs appended for audit trail
- Rate limit errors handled gracefully (return 202 Accepted, schedule retry)
- Template context built from analyses and reports tables

---

#### Task 9.0: POST /api/v1/notify Endpoint
**Dependencies:** Task 8.0

- [x] 9.1 Write 3-5 focused tests for notify endpoint
  - Test POST /api/v1/notify with valid request returns 202 Accepted
  - Test request validation fails with 400 if missing required fields
  - Test notification_ids returned in response
  - Test mocked channel send failures still return 202 (async retry)
  - Run ONLY these 3-5 tests after implementation

- [x] 9.2 Implement POST /api/v1/notify endpoint
  - File: `services/notification-service/src/api/routes.py`
  - Route: POST /api/v1/notify
  - Request model: NotificationRequest
  - Request validation:
    - Check channels list non-empty and valid
    - Check recipients dict contains entries for all channels
    - Check message_type in ['summary', 'alert', 'detailed_report']
  - Call NotificationService.send(request)
  - Return NotificationSuccessResponse with status='processing' (async delivery)
  - HTTP status: 202 Accepted (async operation)
  - Error handling:
    - Validation errors: 400 Bad Request with NotificationErrorResponse
    - Database errors: 500 Internal Server Error
    - Rate limit (all channels): 429 Too Many Requests

- [x] 9.3 Add request ID and correlation tracking
  - File: `services/notification-service/src/api/routes.py`
  - Generate request_id = str(uuid.uuid4())
  - Include in NotificationSuccessResponse
  - Pass to NotificationService for logging context
  - Include in delivery logs (metadata field)
  - Support X-Correlation-ID header if present

- [x] 9.4 Implement response formatting and error mapping
  - File: `services/notification-service/src/api/routes.py`
  - Success response: NotificationSuccessResponse
  - Error response: NotificationErrorResponse
  - Map exception types to error_codes:
    - ValidationError -> 'VALIDATION_ERROR'
    - ChannelError -> 'CHANNEL_ERROR'
    - RateLimitError -> 'RATE_LIMIT_EXCEEDED'
    - ConfigurationError -> 'CONFIGURATION_ERROR'
    - Other errors -> 'INTERNAL_ERROR'

- [x] 9.5 Ensure notify endpoint tests pass
  - Run ONLY the 3-5 tests written in 9.1
  - Verify 202 Accepted returned for valid requests
  - Verify 400 returned for validation errors
  - Verify notification_ids in response
  - Verify error mapping

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- POST /api/v1/notify endpoint implemented
- Request validation with clear error messages
- 202 Accepted response for async delivery
- Notification records created and returned to caller
- Proper error handling and HTTP status codes

---

### Phase 3: Retry & Resilience

#### Task 10.0: Exponential Backoff Retry Logic
**Dependencies:** Task 8.0, Task 9.0

- [x] 10.1 Write 3-5 focused tests for retry mechanism
  - Test exponential backoff calculation: 1s, 2s, 4s, 8s, 16s (2^n)
  - Test max_retries limit prevents infinite loops
  - Test notification marked as failed after max retries exceeded
  - Test retry_count incremented in database
  - Run ONLY these 3-5 tests after implementation

- [x] 10.2 Implement retry logic in NotificationService
  - File: `services/notification-service/src/services/notification_service.py`
  - Method: async def _calculate_next_retry(retry_count: int, max_retries: int) -> Optional[datetime]
    - If retry_count >= max_retries: return None (no more retries)
    - Calculate delay: delay = 2 ** retry_count seconds
    - next_retry = now + timedelta(seconds=delay)
    - Return next_retry datetime
  - In _send_via_channel() when send fails:
    - Increment retry_count
    - Calculate next_retry
    - Store in notifications.metadata['next_retry_at']
    - Update notifications.status = 'retrying'

- [x] 10.3 Create retry scheduler
  - File: `services/notification-service/src/services/retry_scheduler.py`
  - Class: RetryScheduler
  - async def start_scheduler() -> Task
    - Start background task to find and retry pending notifications
  - async def find_retry_eligible_notifications() -> List[str]
    - Query notifications where status='retrying' AND now() >= metadata->>'next_retry_at'
    - Order by metadata->>'next_retry_at' ASC
    - Limit to prevent overwhelming system
  - async def retry_notification(notification_id: str)
    - Get notification record
    - Get associated analysis_id
    - Rebuild template context
    - Call channel.send() again
    - Update status and increment retry_count
    - Insert delivery log entry with attempt_number

- [x] 10.4 Integrate retry scheduler into lifespan
  - File: `services/notification-service/src/main.py`
  - In lifespan startup: start retry_scheduler background task
  - In lifespan shutdown: cancel retry_scheduler task
  - Use asyncio.create_task() for background execution

- [x] 10.5 Ensure retry logic tests pass
  - Run ONLY the 3-5 tests written in 10.1
  - Verify backoff calculation produces correct delays
  - Verify max_retries prevents exceeding limit
  - Verify database updates reflect retry state

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- Exponential backoff calculation: 2^retry_count seconds
- Retry scheduler finds eligible notifications periodically
- Max retries honored (default 5, configurable per channel)
- Notification marked as failed after exhausting retries
- Delivery logs track all retry attempts

---

#### Task 11.0: Rate Limiting Integration with Retry Queue
**Dependencies:** Task 7.0, Task 10.0

- [x] 11.1 Write 3-5 focused tests for rate limit retry
  - Test rate limited notification returns 429 to caller but doesn't fail
  - Test rate limited notification added to retry queue
  - Test retry_after_seconds calculated from token bucket
  - Test notification retried after rate limit window passes
  - Run ONLY these 3-5 tests after implementation

- [x] 11.2 Integrate rate limiting into send flow
  - File: `services/notification-service/src/services/notification_service.py`
  - In _send_via_channel() before calling channel.send():
    - Call channel.check_rate_limit() -> bool
    - If False (rate limited):
      - Get retry_after_seconds from channel.rate_limiter
      - Set next_retry = now + timedelta(seconds=retry_after_seconds)
      - Update notifications: status='retrying', metadata['rate_limited']=True, retry_count unchanged
      - Insert delivery_log with status='rate_limited', retry_after_seconds
      - Return False (will retry later)
    - If True: proceed with send()

- [x] 11.3 Handle rate limit in endpoint response
  - File: `services/notification-service/src/api/routes.py`
  - In POST /api/v1/notify error handling:
    - If RateLimitError caught: return 429 Too Many Requests
    - Include Retry-After header with seconds until retry
    - Return NotificationErrorResponse with error_code='RATE_LIMIT_EXCEEDED'

- [x] 11.4 Ensure rate limit retry tests pass
  - Run ONLY the 3-5 tests written in 11.1
  - Verify rate limited notifications go to retry queue
  - Verify retry_after_seconds calculation from token bucket
  - Verify notification eventually retried when rate limit expires

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- Rate limited requests don't fail immediately (return 202 or 429 with retry info)
- Rate limited notifications added to retry queue with correct retry_after_seconds
- Retry scheduler respects rate limit windows
- Notifications retry successfully after rate limit window passes

---

#### Task 12.0: GET /api/v1/delivery-status Endpoint
**Dependencies:** Task 11.0

- [x] 12.1 Write 3-5 focused tests for delivery status endpoint
  - Test GET /api/v1/delivery-status/{id} returns notification data
  - Test recipient masked in response (email@***, chat****)
  - Test 404 returned for non-existent notification
  - Test delivery logs included in response (last N entries)
  - Run ONLY these 3-5 tests after implementation

- [x] 12.2 Implement GET /api/v1/delivery-status endpoint
  - File: `services/notification-service/src/api/routes.py`
  - Route: GET /api/v1/delivery-status/{notification_id}
  - Query notifications table by notification_id
  - Return DeliveryStatusResponse with:
    - notification_id, analysis_id, channel, recipient (masked), status, sent_at, latency_ms, external_id, retry_count, created_at
  - Include delivery_log entries (last 5-10) for debugging
  - Mask recipient in response:
    - Email: email@*** (show domain)
    - Telegram: 123456****
  - HTTP 404 if notification not found

- [x] 12.3 Create recipient masking utility
  - File: `services/notification-service/src/utils/masking.py`
  - Function: mask_recipient(recipient: str, channel: str) -> str
    - Email: keep first char + domain, mask middle
    - Telegram: show first 6 digits + ***
    - Phone: show country code + ***
  - Use in responses and logs

- [x] 12.4 Ensure delivery status endpoint tests pass
  - Run ONLY the 3-5 tests written in 12.1
  - Verify notification data returned correctly
  - Verify recipient masking applied
  - Verify 404 for non-existent notification

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- GET /api/v1/delivery-status/{id} endpoint returns notification details
- Recipient masking applied in all responses and logs
- Delivery logs queryable for debugging
- HTTP status codes correct (200, 404)

---

### Phase 4: Monitoring & Audit

#### Task 13.0: GET /api/v1/delivery-stats Endpoint
**Dependencies:** Task 12.0

- [x] 13.1 Write 3-5 focused tests for delivery stats
  - Test GET /api/v1/delivery-stats returns aggregated stats
  - Test stats broken down by channel
  - Test success rate calculation
  - Test average latency calculation
  - Run ONLY these 3-5 tests after implementation

- [x] 13.2 Implement GET /api/v1/delivery-stats endpoint
  - File: `services/notification-service/src/api/routes.py`
  - Route: GET /api/v1/delivery-stats?period_days=7
  - Query notifications_delivery_log for last N days (default 7)
  - Return DeliveryStatsResponse with:
    - period_days, total_notifications
    - by_channel: {channel: {total, sent, failed, success_rate, avg_latency_ms}}
    - avg_retries, largest_latency_ms
  - Calculations:
    - success_rate = (sent / total) * 100
    - avg_latency_ms = AVG(latency_ms) for sent notifications
    - avg_retries = AVG(retry_count) across all notifications

- [x] 13.3 Create analytics repository layer
  - File: `services/notification-service/src/db/analytics_repository.py`
  - Class: AnalyticsRepository
  - async def get_delivery_stats(days: int) -> Dict
    - Complex SQL query aggregating notifications_delivery_log
    - Group by channel, calculate percentages and averages
    - Return structured dict for response model

- [x] 13.4 Ensure delivery stats endpoint tests pass
  - Run ONLY the 3-5 tests written in 13.1
  - Verify stats calculated correctly
  - Verify per-channel breakdown
  - Verify success rate and latency metrics

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- GET /api/v1/delivery-stats endpoint returns aggregated statistics
- Per-channel breakdown of delivery performance
- Success rate, latency, retry metrics calculated
- Queryable by time period (days parameter)

---

#### Task 14.0: POST /api/v1/channels Endpoint (Channel Status)
**Dependencies:** Task 3.0

- [x] 14.1 Write 3-5 focused tests for channels endpoint
  - Test GET /api/v1/channels returns list of enabled channels
  - Test channel status includes name, enabled, rate_limit, tokens_available
  - Test disabled channels not included in response
  - Run ONLY these 3-5 tests after implementation

- [x] 14.2 Implement GET /api/v1/channels endpoint
  - File: `services/notification-service/src/api/routes.py`
  - Route: GET /api/v1/channels
  - Query ChannelFactory for all loaded channels
  - For each channel: call get_channel_status()
  - Return ChannelStatusResponse with:
    - channels: [{name, enabled, rate_limit, tokens_available, sender/chat_id}]
    - timestamp
  - Only include enabled channels

- [x] 14.3 Implement Channel.get_channel_status() method
  - File: `services/notification-service/src/channels/base.py`
  - Return dict with:
    - name, enabled, rate_limit (from config)
    - tokens_available (current tokens in rate limiter)
    - channel-specific fields (sender_email for email, chat_id for telegram)

- [x] 14.4 Ensure channels endpoint tests pass
  - Run ONLY the 3-5 tests written in 14.1
  - Verify channel list returned
  - Verify channel status fields present
  - Verify rate limit info included

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- GET /api/v1/channels endpoint returns enabled channels and status
- Channel status includes rate limit and token availability
- Channel-specific configuration visible (sender, bot token masked, etc.)

---

#### Task 15.0: System Logging & Audit Trail
**Dependencies:** Task 9.0, Task 10.0

- [x] 15.1 Write 3-5 focused tests for audit logging
  - Test delivery events logged to system_logs
  - Test failed deliveries logged with error_code
  - Test credentials/sensitive data not logged
  - Test structured logging with context fields
  - Run ONLY these 3-5 tests after implementation

- [x] 15.2 Add logging throughout delivery pipeline
  - File: `services/notification-service/src/services/notification_service.py`
  - In send():
    - logger.info("Sending notifications", extra={report_id, analysis_id, channels})
  - On send success:
    - logger.info("Notification sent", extra={notification_id, channel, recipient (masked), latency_ms})
  - On send failure:
    - logger.error("Notification failed", extra={notification_id, channel, error_code, error_message, retry_count})
  - On rate limit:
    - logger.warning("Rate limited", extra={channel, retry_after_seconds})

- [x] 15.3 Insert system_logs entries for critical events
  - File: `services/notification-service/src/db/system_logs_repository.py`
  - Class: SystemLogsRepository
  - async def log_event(service_name: str, log_level: str, message: str, report_id: str, metadata: Dict)
    - Insert into system_logs table
  - Call from NotificationService for:
    - delivery_completed (success)
    - delivery_failed (failure, with error_code and reason)
    - delivery_retrying (transient failure, scheduled retry)

- [x] 15.4 Implement credential masking in all logs
  - File: `services/notification-service/src/utils/masking.py`
  - Update to mask:
    - Email addresses: user@***
    - Telegram chat IDs: 1234****
    - API keys/tokens: show only last 4 chars (token****)
  - Apply to all logger.* calls using extra parameter

- [x] 15.5 Ensure audit logging tests pass
  - Run ONLY the 3-5 tests written in 15.1
  - Verify events logged with correct structure
  - Verify credentials properly masked
  - Verify system_logs table populated

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- All delivery events logged (success, failure, retry)
- Credentials/sensitive data never logged in full
- Structured logging with context fields (notification_id, channel, etc.)
- system_logs table contains audit trail of all events

---

### Phase 5: Advanced Features & Polish

#### Task 16.0: POST /api/v1/notify/batch Endpoint
**Dependencies:** Task 9.0

- [x] 16.1 Write 3-5 focused tests for batch notifications
  - Test POST /api/v1/notify/batch accepts list of NotificationRequest
  - Test returns 202 with all notification IDs
  - Test validation errors include affected notification indices
  - Run ONLY these 3-5 tests after implementation

- [x] 16.2 Implement POST /api/v1/notify/batch endpoint
  - File: `services/notification-service/src/api/routes.py`
  - Route: POST /api/v1/notify/batch
  - Request model: NotificationBatchRequest (list of NotificationRequest)
  - Process each request sequentially or in parallel (use asyncio.gather for parallel)
  - Collect results and failures
  - Return 202 with all notification_ids and per-notification status
  - If partial failure: still return 202 but include error details for failed items

- [x] 16.3 Ensure batch endpoint tests pass
  - Run ONLY the 3-5 tests written in 16.1
  - Verify batch processing
  - Verify partial failure handling
  - Verify all notification IDs returned

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- POST /api/v1/notify/batch endpoint accepts multiple notifications
- Efficient batch processing (parallel with asyncio.gather)
- Partial failure handling and reporting

---

#### Task 17.0: Template Variants & Message Types
**Dependencies:** Task 6.0

- [x] 17.1 Write 3-5 focused tests for template variants
  - Test render with message_type='alert' uses alert.jinja2
  - Test render with message_type='detailed_report' uses detailed_report.jinja2
  - Test missing template raises TemplateError
  - Run ONLY these 3-5 tests after implementation

- [x] 17.2 Create alert message template variant
  - File: `services/notification-service/templates/email/alert.jinja2` and `telegram/alert.jinja2`
  - Shorter, more concise version of summary
  - Email: plaintext summary with key signals only
  - Telegram: markdown with emoji and essential data only

- [x] 17.3 Create detailed_report message template variant
  - File: `services/notification-service/templates/email/detailed_report.jinja2` and `telegram/detailed_report.jinja2`
  - Full detailed version with complete analysis
  - Email: comprehensive HTML with tables and charts
  - Telegram: multi-message version split across chunks

- [x] 17.4 Ensure template variant tests pass
  - Run ONLY the 3-5 tests written in 17.1
  - Verify correct template selected by message_type
  - Verify all variants render successfully

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- Three template variants (summary, alert, detailed_report) for each channel
- Template selection based on message_type parameter
- All templates validate at startup

---

#### Task 18.0: Dynamic Channel Configuration & Hot-Reload
**Dependencies:** Task 3.0, Task 7.0

- [x] 18.1 Write 3-5 focused tests for hot-reload
  - Test reload_channels() reloads from database
  - Test enable/disable channel via database without restart
  - Test configuration changes take effect immediately
  - Run ONLY these 3-5 tests after implementation

- [x] 18.2 Implement channel configuration hot-reload
  - File: `services/notification-service/src/channels/factory.py`
  - async def reload_channels() -> None
    - Re-query channel_configurations table
    - Instantiate new channel instances
    - Replace in factory's channel dict
    - Log channel enable/disable events
  - async def background_config_reloader() -> Task
    - Periodically (every 5 minutes?) call reload_channels()
    - Check for database changes in channel_configurations

- [x] 18.3 Integrate config reloader into lifespan
  - File: `services/notification-service/src/main.py`
  - Start background config reloader task
  - Stop on shutdown

- [x] 18.4 Add endpoint to manually trigger reload (optional)
  - File: `services/notification-service/src/api/routes.py`
  - Route: POST /api/v1/channels/reload (admin only, optional)
  - Trigger immediate reload without waiting for background task

- [x] 18.5 Ensure hot-reload tests pass
  - Run ONLY the 3-5 tests written in 18.1
  - Verify channels reloaded from database
  - Verify configuration changes take effect

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- Channel enable/disable via database without restart
- Rate limits and configuration updatable at runtime
- Background reloader checks for changes periodically

---

#### Task 19.0: Docker & Docker Compose Integration
**Dependencies:** All previous tasks

- [x] 19.1 Write 3-5 focused tests for docker deployment
  - Test service starts in Docker container
  - Test health check endpoint responds
  - Test environment variables loaded from .env
  - Run ONLY these 3-5 tests after implementation

- [x] 19.2 Create Dockerfile for notification service
  - File: `services/notification-service/Dockerfile`
  - Base image: python:3.11-slim
  - Install dependencies from requirements.txt
  - Create non-root user (notif:1000)
  - Health check: curl http://localhost:8003/health
  - CMD: uvicorn src.main:app --host 0.0.0.0 --port 8003

- [x] 19.3 Create requirements.txt
  - File: `services/notification-service/requirements.txt`
  - Dependencies:
    - fastapi==0.104.1
    - uvicorn==0.24.0
    - pydantic==2.4.2
    - asyncpg==0.29.0
    - aiosmtplib==2.1.0
    - aiohttp==3.9.1
    - jinja2==3.1.2
    - python-dotenv==1.0.0
    - pytest==7.4.3
    - pytest-asyncio==0.21.1
    - httpx==0.25.0

- [x] 19.4 Create .env.example
  - File: `services/notification-service/.env.example`
  - SERVICE_PORT=8003
  - LOG_LEVEL=INFO
  - DATABASE_URL=postgresql://...
  - DATABASE_POOL_MIN=2
  - DATABASE_POOL_MAX=10
  - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL
  - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  - CORRELATION_ID_HEADER=X-Correlation-ID

- [x] 19.5 Update docker-compose.yml
  - File: `docker-compose.yml`
  - Add notification-service:
    - build: ./services/notification-service
    - container_name: trading-notification
    - ports: 8003:8003
    - environment: (from .env via env_file)
    - depends_on: postgres (service_healthy)
    - networks: trading
    - restart: unless-stopped
    - healthcheck: GET /health

- [x] 19.6 Ensure docker deployment tests pass
  - Run ONLY the 3-5 tests written in 19.1
  - Verify container starts successfully
  - Verify health check passes
  - Verify service responds to requests

**Acceptance Criteria:**
- 3-5 focused tests written and all pass
- Dockerfile builds successfully
- Service runs in Docker container
- Environment variables loaded correctly
- Health check endpoint responds
- docker-compose integration working

---

#### Task 20.0: End-to-End Integration & Manual Testing
**Dependencies:** All previous tasks

- [x] 20.1 Write 3-5 focused end-to-end tests
  - Test full flow: request -> DB write -> channel send -> log entry
  - Test retry flow: failure -> retry scheduled -> retry succeeds
  - Test rate limiting: exceed limit -> 429 -> retry after succeeds
  - Run ONLY these 3-5 tests after implementation

- [x] 20.2 Create conftest.py for test fixtures
  - File: `services/notification-service/tests/conftest.py`
  - Fixture: db (test database with migrations)
  - Fixture: client (FastAPI TestClient)
  - Fixture: mock_smtp (mocked SMTP server)
  - Fixture: mock_telegram (mocked Telegram API)
  - Fixture: notification_service (service instance)
  - Fixture: sample_analysis (test analysis data)

- [x] 20.3 Create test_e2e_full_flow.py
  - File: `services/notification-service/tests/test_e2e_full_flow.py`
  - Test: POST /api/v1/notify -> notification created -> channels called -> logs appended
  - Test: GET /api/v1/delivery-status returns correct status
  - Test: GET /api/v1/delivery-stats aggregates correctly
  - Use mocked SMTP and Telegram to avoid external calls

- [x] 20.4 Create test_e2e_retry_flow.py
  - File: `services/notification-service/tests/test_e2e_retry_flow.py`
  - Test: Send fails -> retry scheduled -> eventual success
  - Test: Max retries exceeded -> marked failed
  - Test: Exponential backoff timing correct

- [x] 20.5 Create test_e2e_rate_limiting.py
  - File: `services/notification-service/tests/test_e2e_rate_limiting.py`
  - Test: Consume rate limit tokens -> return 429 -> retry later
  - Test: Tokens refill over time -> retry succeeds
  - Test: Per-channel independent limits

- [x] 20.6 Manual testing checklist
  - Start all services: make dev
  - POST to /api/v1/notify with valid email and telegram
  - Verify notifications created in database
  - Verify delivery logs appended
  - Verify channel responses logged correctly
  - Verify GET /health returns ok
  - Verify GET /api/v1/channels lists email and telegram
  - Verify GET /api/v1/delivery-stats returns metrics
  - Simulate rate limit (fast requests) -> verify 429 handling
  - Simulate SMTP failure -> verify retry scheduled
  - Verify Telegram message split for long text

- [x] 20.7 Ensure e2e tests pass
  - Run ONLY the 3-5 tests written in 20.1 plus additional e2e test files
  - Run: pytest services/notification-service/tests/test_e2e_*.py -v
  - Verify all critical workflows covered

**Acceptance Criteria:**
- 3-5 focused end-to-end tests written and passing
- Complete test fixtures for database and mock APIs
- Full flow testing: request -> DB -> channels -> logs
- Retry and rate limiting workflows tested
- Manual testing checklist completed successfully
- All services running and integrated via docker-compose

---

### Testing Summary

#### Task 21.0: Test Coverage Review & Strategic Gap Filling
**Dependencies:** All Tasks 1-20

- [x] 21.1 Review tests from all phases
  - Count tests written: approximately 3-5 per task * 20 tasks = 60-100 tests
  - All tests are focused on core workflows, not exhaustive coverage
  - Tests use mocks for external dependencies (SMTP, Telegram, database)

- [x] 21.2 Analyze critical gaps in test coverage
  - Identify workflows NOT covered by phase tests
  - Examples of critical gaps to consider:
    - Concurrent notifications (asyncio.gather behavior under load)
    - Template rendering with malformed template variables
    - Database connection pool exhaustion
    - Large message handling (splitting logic)
    - Credential masking in all code paths
  - BUT: Only add tests if gaps are CRITICAL to business requirements

- [x] 21.3 Write maximum 10 additional strategic tests
  - Target: fill identified critical gaps only
  - Examples:
    - test_concurrent_notifications_async_gather.py
    - test_large_message_splitting_edge_cases.py
    - test_database_pool_exhaustion_handling.py
  - Each test: 1-2 test functions, focused on one critical scenario
  - Do NOT write comprehensive coverage or edge case tests

- [x] 21.4 Run feature-specific tests only
  - Total feature tests: 60-100 (from phases) + up to 10 (gap filling) = 70-110 tests
  - Run ONLY tests related to notification service feature
  - Command: pytest services/notification-service/tests/ -v --tb=short
  - Exclude: entire application test suite, other services' tests
  - Verify all pass

**Acceptance Criteria:**
- All phase tests (60-100) pass
- Maximum 10 additional strategic tests written and passing
- Total: 70-110 tests covering critical workflows
- No more than 10 gap-filling tests added
- All feature-specific tests passing
- Entire application test suite NOT run at this stage

---

### Deployment & Operations

#### Task 22.0: Service Documentation & README
**Dependencies:** All previous tasks

- [x] 22.1 Create README.md
  - File: `services/notification-service/README.md`
  - Overview: service purpose and key features
  - Architecture: channels, templates, retry logic
  - Installation: dependencies, setup steps
  - Configuration: environment variables and database config
  - API: endpoint documentation with curl examples
  - Testing: how to run tests
  - Troubleshooting: common issues and debugging

- [x] 22.2 Create API documentation
  - File: `services/notification-service/docs/API.md`
  - Detailed endpoint specifications with examples
  - Request/response models
  - Error codes and status codes
  - Rate limiting behavior
  - Include curl examples for each endpoint

- [x] 22.3 Create deployment guide
  - File: `services/notification-service/docs/DEPLOYMENT.md`
  - Docker build and run commands
  - docker-compose integration
  - Environment setup
  - Database migrations
  - Health checks and monitoring
  - Rollback procedure

- [x] 22.4 Create troubleshooting guide
  - File: `services/notification-service/docs/TROUBLESHOOTING.md`
  - Common issues: SMTP failures, Telegram auth, rate limiting
  - Debugging: logs, SQL queries, service status
  - Performance tuning: pool size, rate limits, template caching

**Acceptance Criteria:**
- README.md explains service purpose and setup
- API.md documents all endpoints with examples
- DEPLOYMENT.md covers Docker and production setup
- TROUBLESHOOTING.md helps resolve common issues

---

#### Task 23.0: Monitoring & Alerting Setup
**Dependencies:** Task 15.0

- [x] 23.1 Define monitoring metrics
  - Key metrics: delivery success rate, latency, retry rate, rate limit hits
  - Set targets: >99% success, <10s email latency, <5s Telegram latency
  - Create queries to extract metrics from notifications_delivery_log

- [x] 23.2 Create monitoring queries
  - File: `database/monitoring/notification_delivery.md` (already exists, update if needed)
  - Queries for:
    - Delivery success rate per channel
    - Average latency per channel
    - Failed notifications needing intervention
    - Rate limit events

- [x] 23.3 Create alerting rules (optional, Phase 2+)
  - Define alert conditions: success rate < 95%, avg latency > 15s
  - Configure notifications to operator (email/Telegram/Slack)
  - Set up automated incident response (re-enable retries, restart service, etc.)

**Acceptance Criteria:**
- Monitoring metrics defined and queryable
- Dashboard queries created
- Alerting rules documented (implementation in future phase)

---

#### Task 24.0: Performance & Load Testing
**Dependencies:** Task 19.0

- [x] 24.1 Create load test scenario
  - File: `services/notification-service/tests/load_test.py` (optional, Phase 2+)
  - Simulate concurrent notification requests
  - Measure latency and throughput
  - Identify bottlenecks

- [x] 24.2 Document performance baselines
  - Expected throughput: notifications/second
  - Expected latency: p50, p95, p99
  - Database connection pool saturation point

**Acceptance Criteria:**
- Load test scenario documented
- Performance baselines established
- Bottlenecks identified for future optimization

---

## Execution Order

**Recommended implementation sequence** (follow task numbers):

1. **Phase 1 (Tasks 1-2)**: Core infrastructure
   - Database migrations and connection pool
   - FastAPI app, config, exception handling, logging
   - Enable basic health check before moving to channels

2. **Phase 2 (Tasks 3-9)**: Channel implementations
   - Base Channel and ChannelFactory
   - Email and Telegram channels with SMTP/Bot API
   - Template system with Jinja2
   - Rate limiting with TokenBucket
   - NotificationService orchestration
   - /notify endpoint

3. **Phase 3 (Tasks 10-12)**: Reliability
   - Retry logic with exponential backoff
   - Rate limiting integration
   - Delivery status endpoint

4. **Phase 4 (Tasks 13-15)**: Monitoring
   - Delivery statistics endpoint
   - Channel status endpoint
   - System logging and audit trail

5. **Phase 5 (Tasks 16-20)**: Advanced features and integration
   - Batch notifications endpoint
   - Template variants (alert, detailed_report)
   - Hot-reload configuration
   - Docker integration
   - End-to-end testing

6. **Final (Tasks 21-24)**: Documentation and operations
   - Test coverage review and gap filling
   - Service documentation
   - Monitoring setup
   - Performance testing

---

## Dependencies Summary

```
Task 1 (DB Migrations)
  ↓
Task 2 (Config & Core)
  ↓
Task 3 (Channel Base & Factory)
  ├─→ Task 4 (Email)
  ├─→ Task 5 (Telegram)
  ├─→ Task 6 (Templates) ← Dependencies: 2, 4, 5
  ├─→ Task 7 (Rate Limiter)
  └─→ Task 8 (NotificationService) ← Dependencies: 3, 4, 5, 6, 7
        ↓
      Task 9 (/notify endpoint)
        ├─→ Task 10 (Retry logic)
        │     ↓
        │   Task 11 (Rate limit retry)
        │     ↓
        │   Task 12 (Delivery status)
        ├─→ Task 13 (Delivery stats)
        ├─→ Task 14 (Channels endpoint)
        └─→ Task 15 (Audit logging)

Task 16 (Batch) ← Task 9
Task 17 (Variants) ← Task 6
Task 18 (Hot-reload) ← Task 3, 7
Task 19 (Docker) ← All previous

Task 20 (E2E Testing) ← All previous
Task 21 (Test gaps) ← All previous
Task 22 (Docs) ← All previous
Task 23 (Monitoring) ← Task 15
Task 24 (Load testing) ← Task 19
```

---

## Key Implementation Notes

### Pattern Consistency
- Follow `services/ai-analyzer/` patterns for:
  - Config class in config.py
  - FastAPI setup with lifespan in main.py
  - Pydantic models in models.py
  - Exception hierarchy in utils/exceptions.py
  - Database pool in db/connection.py
  - Structured logging in utils/logger.py

### Database Design
- Use existing `notifications` table from schema
- Create two new tables: `notifications_delivery_log` (append-only), `channel_configurations` (runtime config)
- All queries use parameterized statements to prevent SQL injection
- Indexes on frequently-queried columns: notification_id, channel, created_at

### Testing Approach
- 2-8 tests per task group (actual range varies by task complexity)
- Focus on core behaviors, not exhaustive coverage
- Mock external dependencies (SMTP, Telegram, database)
- Run ONLY task-specific tests during development (not entire suite)
- End-to-end tests use Docker for integration validation

### Error Handling
- Custom exception hierarchy for specific error types
- Transient failures (timeout, SMTP 421): add to retry queue, return 202
- Permanent failures (invalid email, auth failure): mark failed, return 400
- Database failures: return 500, log CRITICAL
- Never lose notification: always persist before attempting delivery

### Security
- Never log full credentials or sensitive data (email@***, token****)
- Validate SSL/TLS for SMTP
- Sanitize message content before sending
- Support credential rotation via environment variables (no restart)
- Validate all input at API boundaries

### Performance
- Use asyncio.gather() for parallel channel operations
- Token bucket rate limiting prevents external API throttling
- Database connection pooling for concurrent requests
- Lazy template loading with caching
- Paginate large result sets in monitoring queries

---

## Success Criteria

**Phase 1 Complete**: Service starts, config loads, database connections work, health check responds
**Phase 2 Complete**: Notifications send via email and Telegram, templates render, rate limiting active
**Phase 3 Complete**: Failed notifications retry with backoff, delivery status queryable
**Phase 4 Complete**: Delivery statistics available, channel status visible, audit logs recorded
**Phase 5 Complete**: Batch notifications work, templates variants available, Docker deployment, E2E tests pass
**Final Complete**: Documentation written, monitoring configured, all tests passing, ready for production

---

## File Manifest

**Core Service Files**:
- services/notification-service/src/main.py
- services/notification-service/src/config.py
- services/notification-service/src/models.py
- services/notification-service/src/utils/exceptions.py
- services/notification-service/src/utils/logger.py
- services/notification-service/src/utils/masking.py
- services/notification-service/src/utils/rate_limiter.py

**Database Layer**:
- services/notification-service/src/db/connection.py
- services/notification-service/src/db/notifications_repository.py
- services/notification-service/src/db/analytics_repository.py
- services/notification-service/src/db/system_logs_repository.py
- database/migrations/007_create_notifications_delivery_log.sql
- database/migrations/008_create_channel_configurations.sql

**Channels & Templates**:
- services/notification-service/src/channels/base.py
- services/notification-service/src/channels/factory.py
- services/notification-service/src/channels/email.py
- services/notification-service/src/channels/smtp_client.py
- services/notification-service/src/channels/telegram.py
- services/notification-service/src/channels/telegram_client.py
- services/notification-service/src/templates/engine.py
- services/notification-service/templates/email/summary.jinja2
- services/notification-service/templates/email/alert.jinja2
- services/notification-service/templates/email/detailed_report.jinja2
- services/notification-service/templates/telegram/summary.jinja2
- services/notification-service/templates/telegram/alert.jinja2
- services/notification-service/templates/telegram/detailed_report.jinja2
- services/notification-service/templates/shared/macros.jinja2

**API & Services**:
- services/notification-service/src/api/routes.py
- services/notification-service/src/services/notification_service.py
- services/notification-service/src/services/retry_scheduler.py

**Tests**:
- services/notification-service/tests/conftest.py
- services/notification-service/tests/test_*.py (task-specific tests)
- services/notification-service/tests/test_e2e_*.py (end-to-end tests)

**Configuration & Deployment**:
- services/notification-service/Dockerfile
- services/notification-service/requirements.txt
- services/notification-service/.env.example
- services/notification-service/README.md
- services/notification-service/docs/API.md
- services/notification-service/docs/DEPLOYMENT.md
- services/notification-service/docs/TROUBLESHOOTING.md
- docker-compose.yml (updated)

---

**Total Estimated Effort**: 80-120 development hours
**Recommended Team**: 1-2 backend engineers, 1 QA engineer
**Timeline**: 3-4 weeks with parallel task execution
