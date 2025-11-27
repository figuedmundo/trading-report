# Specification: Unified Notification Service

## Goal

Consolidate email and Telegram notification delivery into a single, extensible multi-channel notification service that sends AI-generated trading analysis summaries with signal highlights, source metadata, timestamps, and confidence metrics. Replace two separate notification services with a unified factory-based architecture supporting configuration-driven channel registration and future extensibility for SMS, Slack, Discord, and other channels.

## User Stories

- As a trader, I want to receive trading analysis summaries via my preferred channels (email, Telegram) with clear formatting, signal highlights, and actionable information so I can act on trading opportunities quickly
- As a system operator, I want to manage notification delivery, retry logic, and channel configuration in a single service with complete audit trails and monitoring visibility so I can maintain reliable multi-channel notification delivery
- As a developer, I want to add new notification channels (SMS, Slack, Discord) by implementing a simple channel interface and registering in configuration, without modifying existing channels or core service logic

## Specific Requirements

**Service Consolidation**
- Replace roadmap items 7 (Email Notification Service) and 8 (Telegram Notification Service) with single unified service
- Single FastAPI application serving all notification channels
- Channel-agnostic core with pluggable channel implementations
- Backward compatible with N8N workflow integration patterns

**Channel Architecture & Registration**
- Implement channel factory pattern with base Channel abstract class
- Configuration-driven channel registration (no code changes required to add channels)
- Channels registered via environment variables and database configuration table
- Support for channels: email, telegram, and framework for SMS, Slack, Discord, webhook
- Each channel implementation handles its own formatting, API integration, and error handling

**Message Templates & Rendering**
- Use Jinja2 template engine for dynamic message generation
- Channel-specific templates stored in `services/notification-service/templates/` directory
- Template structure: `{channel_name}/{message_type}.jinja2` (e.g., `email/summary.jinja2`, `telegram/summary.jinja2`)
- Base template variables: report_title, summary, trading_signals, sentiment, confidence_score, report_url, timestamp
- Support template variants for different message types (summary, alert, detailed_report)
- Template validation during service startup with clear error messages for missing templates

**Email Channel**
- Use SMTP for delivery (Gmail, Outlook, custom SMTP servers)
- Configuration: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL
- Support HTML and plain text email templates
- Include trading signal highlights, confidence metrics in formatted HTML
- Recipient validation (must be valid email address)
- Delivery timeout: 10 seconds per email
- Fallback to plain text if HTML rendering fails

**Telegram Channel**
- Use Telegram Bot API for message delivery
- Configuration: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (or per-user mapping)
- Support formatted messages with emoji and markdown for readability
- Message length limit: 4096 characters (split into multiple messages if needed)
- Recipient validation (must be numeric chat ID)
- Delivery timeout: 5 seconds per message
- Include message links to web dashboard if available

**Retry Mechanism with Exponential Backoff**
- Database-backed retry queue stored in notifications table
- Retry schedule: 1s, 2s, 4s, 8s, max 5 retries (configurable per channel)
- Calculate next retry as: `next_retry = now + (2 ^ retry_count) seconds`
- Store retry_count and max_retries in notifications record
- Log each retry attempt in system_logs with failure reason
- Mark notification as failed after max retries exceeded
- Re-raise exceptions after final retry for operator alerting

**Rate Limiting per Channel**
- Implement token bucket algorithm per channel (not global)
- Email: 100 messages per hour (rate limit prevents SMTP server throttling)
- Telegram: 30 messages per minute (within Telegram API limits, allows batching)
- Custom rate limits configurable per channel via database settings
- Track token refill rate and last message timestamp in memory (not persisted)
- Return 429 error if rate limit exceeded; add to retry queue for later delivery
- Log rate limiting events at WARNING level with calculated retry_after

**Audit Trail & Delivery Logging**
- Log all notification delivery attempts to notifications_delivery_log table (JSONB append-only)
- Track: channel, recipient, status, sent_at, delivery_latency_ms, error_code, error_message, retry_count
- Update notifications table status field (pending → sent/failed/retrying)
- Store complete message content for audit trail and debugging
- Include external message IDs (email Message-ID, Telegram message_id) for tracking
- Log successful delivery with latency_ms metric for performance monitoring
- Log failures with error_code and error_message for root cause analysis

**Configuration Management**
- Environment variables for secrets: SMTP_PASSWORD, TELEGRAM_BOT_TOKEN, API keys
- Database table: channel_configurations (channel_name, setting_key, setting_value, is_active)
- Hybrid approach: secrets in env vars, channel settings in database
- Load configuration during service startup; cache in memory with hourly refresh
- Validate all configuration at startup; fail fast if required settings missing
- Support runtime channel enable/disable via database without redeployment

**API Endpoints**
- POST /api/v1/notify - Send notification to one or more channels
- POST /api/v1/notify/batch - Send batch notifications (multiple recipients/channels)
- GET /api/v1/delivery-status/{notification_id} - Query delivery status
- GET /api/v1/delivery-stats - Aggregate delivery statistics (success rate, latency, retries)
- POST /api/v1/channels - List enabled channels and their status
- GET /health - Health check endpoint

**Request/Response Models**
- POST /api/v1/notify request: analysis_id, report_id, channels (email, telegram), recipients, message_type
- POST /api/v1/notify response: notification_ids (array of created notification records), status
- Response includes request_id for correlation, timestamp, duration_ms
- Error responses include error_code, error_message, and affected_channels (which channels failed)

**Error Handling & Failures**
- Custom exception hierarchy: NotificationError (base), ChannelError, TemplateError, ConfigurationError, RateLimitError
- Transient failures (SMTP timeout, API error): add to retry queue; return 202 Accepted
- Permanent failures (invalid email, auth failure): mark as failed; return 400 Bad Request
- Validation failures (missing required fields): return 400 before creating notification record
- Database failures: return 500; log CRITICAL error with full traceback
- Never lose notification due to error; always persist to database first, then attempt delivery

**Service Structure**
- Create FastAPI app with lifespan context manager for startup/shutdown
- Separate files: config.py, models.py, channels/ (abstract base + implementations), templates/, routes/, services/
- Channel base class: abstract methods handle_send(), validate_config(), get_channel_status()
- Channel implementations: EmailChannel, TelegramChannel (and future SMS, Slack, etc.)
- NotificationService: coordinates channel instantiation, message rendering, retry logic
- ChannelFactory: loads channels from configuration and instantiates
- Include /health endpoint returning service status and channel health

**Logging Strategy**
- Log all notification send attempts with report_id, channel, recipient (masked), timestamp
- Log successful delivery with external message ID and latency_ms
- Log failures with error_code, error_message, and retry_count
- Use structured logging with context fields: report_id, notification_id, channel, attempt_number
- Log configuration loading errors as CRITICAL (service startup fails if critical config missing)
- Log rate limiting events as WARNING with refill calculation details

**Database Integration**
- Read: notifications table (id, analysis_id, channel, recipient, status, retry_count, max_retries, message_content)
- Write: notifications.status, notifications.sent_at, notifications.retry_count, notifications.updated_at
- Write: notifications_delivery_log (append-only audit trail with full delivery metadata)
- Create: notifications records for each channel (one email + one telegram notification per analysis)
- Query: Find pending/retrying notifications with backoff calculation (exponential delay)
- Transactions: Update notification status only after confirmed delivery; rollback on database errors

**Security & Secrets Management**
- Never log email addresses, phone numbers, or chat IDs in full (mask in logs: email@***, 123456****)
- Never log API keys, tokens, or credentials (log only key name, not value)
- Store API keys/passwords in environment variables only (never in database or logs)
- Validate SSL/TLS certificates for SMTP connections (reject self-signed without explicit override)
- Sanitize message content before sending (remove any embedded credentials or sensitive data)
- Support credential rotation via environment variable update (no service restart needed)

## Visual Design

(No visual mockups provided for service architecture specification)

## Existing Code to Leverage

**Config Class Pattern (services/ai-analyzer/src/config.py)**
- Use same Config class approach: load environment variables at startup
- Implement property-based structure for easy testing and documentation
- Use validate_config() function to check required fields at initialization
- Support optional fields with sensible defaults (rate_limit_per_hour, retry_max_attempts)
- Follow ConfigurationError exception pattern for validation failures

**FastAPI Service Template (services/ai-analyzer/src/main.py)**
- Use asynccontextmanager for lifespan management (startup/shutdown handlers)
- Include CORS middleware for service-to-service communication
- Add router include pattern for modular route organization
- Implement health check endpoint returning service status and version
- Use logger for startup/shutdown events

**Pydantic Models for Validation (services/ai-analyzer/src/models.py)**
- Create request models (NotificationRequest) with field validators
- Create response models (NotificationSuccessResponse, NotificationErrorResponse)
- Use field_validator decorators for input validation
- Follow naming convention: RequestName, SuccessResponseName, ErrorResponseName
- Include optional fields with defaults (e.g., retry_max_attempts: int = 5)

**Exception Pattern (services/ai-analyzer/src/utils/exceptions.py)**
- Create exception module with custom exception hierarchy
- Base exception class with message and error_type fields
- Child exceptions: ChannelError, TemplateError, RateLimitError, ValidationError
- Use exception types for targeted error handling in route handlers
- Include __str__() method for logging and user-facing error messages

**Database Connection Pool Pattern (services/ai-analyzer/src/db/connection.py)**
- Use async connection pool for concurrent request handling
- Initialize pool during service startup; close during shutdown
- Implement async context manager pattern for transaction management
- Use parameterized queries to prevent SQL injection
- Include retry logic for connection failures with exponential backoff

**Async/Await Pattern (services/ai-analyzer/src/api/routes.py)**
- Use async functions for all I/O operations (API calls, database, email/Telegram)
- Implement concurrent request handling via FastAPI async route handlers
- Use asyncio.gather() for parallel channel operations (send email and Telegram simultaneously)
- Follow async pattern in service methods for non-blocking execution

**Logging Pattern (services/ai-analyzer/src/utils/logger.py)**
- Use Python logging module with structured format
- Create logger per module using get_logger(__name__)
- Include timestamp, log level, service name, correlation_id in logs
- Use extra parameter for contextual fields: logger.info("msg", extra={"report_id": id})
- Support LOG_LEVEL environment variable for runtime configuration

## Out of Scope

- Push notifications (mobile app notifications)
- SMS delivery via Twilio or other SMS provider (designed for Phase 2, but not implemented)
- Slack or Discord integration (designed for Phase 2+, but not implemented)
- Webhook/custom HTTP endpoint delivery (designed for Phase 2+, but not implemented)
- Message scheduling or delayed delivery (notifications sent immediately, no future scheduling)
- Notification preferences per user (single global settings only, multi-user support deferred)
- HTML email template rendering to plain text fallback (manual plain text templates required)
- Delivery confirmation via webhooks from email/Telegram providers (rely on synchronous response only)
- A/B testing of message templates or personalization beyond signal highlights
- Real-time notification status updates via WebSocket or Server-Sent Events
- Notification aggregation (batching multiple reports into single message)
- Digital signatures or GPG encryption for messages
- Internationalization/localization (all templates in English)
- Message attachment support (files, images only via URLs, not embedded)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Unified Notification Service                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ FastAPI HTTP Layer                                          │    │
│  ├────────────────────────────────────────────────────────────┤    │
│  │ POST /api/v1/notify                                         │    │
│  │ POST /api/v1/notify/batch                                   │    │
│  │ GET  /api/v1/delivery-status/{id}                           │    │
│  │ GET  /api/v1/delivery-stats                                 │    │
│  │ GET  /api/v1/channels                                       │    │
│  │ GET  /health                                                │    │
│  └────────────────────────────────────────────────────────────┘    │
│                              ↓                                       │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ NotificationService (Orchestration Layer)                   │    │
│  ├────────────────────────────────────────────────────────────┤    │
│  │ • Message rendering (Jinja2 templates)                      │    │
│  │ • Channel selection based on request                        │    │
│  │ • Retry logic with exponential backoff                      │    │
│  │ • Rate limiting per channel (token bucket)                  │    │
│  │ • Database transaction management                           │    │
│  │ • Audit logging and metrics collection                      │    │
│  └────────────────────────────────────────────────────────────┘    │
│                              ↓                                       │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ ChannelFactory (Channel Instantiation)                      │    │
│  ├────────────────────────────────────────────────────────────┤    │
│  │ • Loads enabled channels from database config               │    │
│  │ • Instantiates channel implementations                      │    │
│  │ • Validates channel configuration at startup                │    │
│  │ • Handles channel enable/disable without restart            │    │
│  └────────────────────────────────────────────────────────────┘    │
│                      ↙      ↓      ↘                                │
│        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│        │ EmailChannel │  │TelegramChan. │  │ SMSChannel   │        │
│        │ (Impl.)      │  │ (Impl.)      │  │ (Framework)  │        │
│        └──────────────┘  └──────────────┘  └──────────────┘        │
│               │                  │                 │                │
│               ↓                  ↓                 ↓                │
│        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│        │ SMTP Server  │  │ Telegram API │  │ SMS Gateway  │        │
│        │ (External)   │  │ (External)   │  │ (External)   │        │
│        └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Data Layer                                                  │    │
│  ├────────────────────────────────────────────────────────────┤    │
│  │ • notifications table (status tracking, retry metadata)     │    │
│  │ • notifications_delivery_log table (append-only audit)      │    │
│  │ • channel_configurations table (runtime channel config)     │    │
│  │ • system_logs table (delivery events and errors)            │    │
│  └────────────────────────────────────────────────────────────┘    │
│                              ↓                                       │
│        ┌───────────────────────────────────────────────────┐        │
│        │        PostgreSQL 15+ Database                    │        │
│        │  (notifications, delivery logs, audit trail)      │        │
│        └───────────────────────────────────────────────────┘        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

Incoming Request Flow:
  1. POST /api/v1/notify → NotificationController validates request
  2. NotificationService.send() creates notification records in DB
  3. ChannelFactory instantiates enabled channels
  4. For each channel: render template + send via implementation
  5. Update notification status (sent/failed/retrying)
  6. Log delivery event to system_logs
  7. Return response with notification IDs and status
  8. Async retry handler picks up failed notifications periodically

Rate Limiting Flow:
  1. Check channel token bucket (tokens available?)
  2. If yes: decrement tokens, proceed with send
  3. If no: increment retry_count, schedule for later, return 429
  4. Tokens refill at channel-specific rate (e.g., 100/hour for email)
  5. Next eligible time = now + refill_interval * (max_tokens - current_tokens)
```

## Channel Implementation Details

### Base Channel Abstract Class

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class Channel(ABC):
    """Abstract base class for notification channels."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize channel with name and configuration."""
        self.name = name  # 'email', 'telegram', 'sms', etc.
        self.config = config
        self.rate_limiter = None  # TokenBucket instance

    @abstractmethod
    async def send(self, message: str, recipient: str) -> Dict[str, Any]:
        """
        Send message to recipient via this channel.

        Returns: {
            'success': bool,
            'external_id': str (email Message-ID or Telegram message_id),
            'latency_ms': int,
            'error_code': str (if failed),
            'error_message': str (if failed)
        }
        """
        pass

    @abstractmethod
    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient format for this channel."""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate that all required configuration is present."""
        pass

    def get_channel_status(self) -> Dict[str, Any]:
        """Return channel status: enabled, rate_limit, last_sent_at, etc."""
        return {
            'name': self.name,
            'enabled': True,
            'rate_limit': self.config.get('rate_limit_per_hour'),
            'tokens_available': self.rate_limiter.tokens if self.rate_limiter else 0
        }

    async def check_rate_limit(self) -> bool:
        """Check if channel is rate limited; return True if can proceed."""
        if not self.rate_limiter:
            return True
        return await self.rate_limiter.try_consume(1)
```

### Email Channel Implementation

```python
class EmailChannel(Channel):
    """SMTP email delivery channel."""

    async def send(self, message: str, recipient: str) -> Dict[str, Any]:
        """Send email via SMTP."""
        # Validate recipient email
        if not self.validate_recipient(recipient):
            return {
                'success': False,
                'external_id': None,
                'error_code': 'INVALID_EMAIL',
                'error_message': f'Invalid email address: {recipient}'
            }

        # Render HTML and plain text versions
        html_content = message  # Already templated with HTML
        text_content = self._html_to_text(html_content)

        # Send via SMTP with timeout
        try:
            message_id = await self._send_smtp(
                to_addr=recipient,
                html_body=html_content,
                text_body=text_content,
                timeout_seconds=10
            )
            return {
                'success': True,
                'external_id': message_id,  # RFC 5322 Message-ID
                'latency_ms': elapsed_ms,
                'error_code': None
            }
        except SMTPException as e:
            return {
                'success': False,
                'external_id': None,
                'error_code': e.smtp_code,  # e.g., 550, 421
                'error_message': str(e)
            }

    def validate_recipient(self, recipient: str) -> bool:
        """Validate email format using regex."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, recipient))

    def validate_config(self) -> bool:
        """Check SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD."""
        required = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD']
        return all(key in self.config for key in required)
```

### Telegram Channel Implementation

```python
class TelegramChannel(Channel):
    """Telegram Bot API delivery channel."""

    async def send(self, message: str, recipient: str) -> Dict[str, Any]:
        """Send message via Telegram Bot API."""
        # Validate recipient (must be numeric chat ID)
        if not self.validate_recipient(recipient):
            return {
                'success': False,
                'external_id': None,
                'error_code': 'INVALID_CHAT_ID',
                'error_message': f'Invalid Telegram chat ID: {recipient}'
            }

        # Split message if exceeds 4096 character limit
        messages_to_send = self._split_message(message, 4096)

        try:
            message_ids = []
            for chunk in messages_to_send:
                msg_id = await self._send_telegram(
                    chat_id=recipient,
                    text=chunk,
                    parse_mode='Markdown',
                    timeout_seconds=5
                )
                message_ids.append(msg_id)

            return {
                'success': True,
                'external_id': '|'.join(message_ids),  # Multiple IDs if split
                'latency_ms': elapsed_ms,
                'error_code': None
            }
        except TelegramError as e:
            return {
                'success': False,
                'external_id': None,
                'error_code': e.error_code,  # Telegram error code
                'error_message': str(e)
            }

    def validate_recipient(self, recipient: str) -> bool:
        """Validate Telegram chat ID (numeric only)."""
        try:
            int(recipient)
            return True
        except ValueError:
            return False

    def validate_config(self) -> bool:
        """Check TELEGRAM_BOT_TOKEN."""
        return 'TELEGRAM_BOT_TOKEN' in self.config
```

### Token Bucket Rate Limiter

```python
class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Max tokens in bucket (e.g., 100 for 100 emails/hour)
            refill_rate: Tokens per second (e.g., 100/3600 = 0.0278 for 100/hour)
        """
        self.capacity = capacity
        self.tokens = capacity  # Start full
        self.refill_rate = refill_rate
        self.last_refill = asyncio.get_event_loop().time()

    async def try_consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens; return True if successful."""
        await self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    async def _refill(self):
        """Refill tokens based on elapsed time."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now

    def get_retry_after_seconds(self) -> int:
        """Calculate seconds until next token available."""
        if self.tokens >= 1:
            return 0
        needed = 1 - self.tokens
        return int(math.ceil(needed / self.refill_rate))
```

## API Endpoint Specifications

### POST /api/v1/notify

Send notification(s) for an analysis to specified channels.

**Request:**
```json
{
  "analysis_id": "uuid",
  "report_id": "uuid",
  "channels": ["email", "telegram"],
  "recipients": {
    "email": "user@example.com",
    "telegram": "123456789"
  },
  "message_type": "summary"
}
```

**Response (202 Accepted - async delivery):**
```json
{
  "request_id": "req-uuid",
  "status": "processing",
  "notification_ids": ["notif-id-1", "notif-id-2"],
  "timestamp": "2025-11-27T14:30:45Z",
  "channels_created": {
    "email": "success",
    "telegram": "success"
  },
  "duration_ms": 45
}
```

**Error Response (400 Bad Request):**
```json
{
  "request_id": "req-uuid",
  "error": "Missing required field: recipients",
  "error_code": "VALIDATION_ERROR",
  "affected_channels": [],
  "timestamp": "2025-11-27T14:30:45Z"
}
```

### GET /api/v1/delivery-status/{notification_id}

Query delivery status of a specific notification.

**Response:**
```json
{
  "notification_id": "notif-uuid",
  "analysis_id": "uuid",
  "channel": "email",
  "recipient": "user@***",
  "status": "sent",
  "sent_at": "2025-11-27T14:30:52Z",
  "latency_ms": 7250,
  "external_id": "Message-ID-from-smtp@example.com",
  "retry_count": 0,
  "created_at": "2025-11-27T14:30:45Z"
}
```

### GET /api/v1/delivery-stats

Aggregate delivery statistics across all notifications.

**Response:**
```json
{
  "period_days": 7,
  "total_notifications": 150,
  "by_channel": {
    "email": {
      "total": 100,
      "sent": 98,
      "failed": 2,
      "success_rate": 98.0,
      "avg_latency_ms": 5234
    },
    "telegram": {
      "total": 50,
      "sent": 50,
      "failed": 0,
      "success_rate": 100.0,
      "avg_latency_ms": 2100
    }
  },
  "avg_retries": 0.35,
  "largest_latency_ms": 45000
}
```

### POST /api/v1/channels

List enabled channels and their configuration.

**Response:**
```json
{
  "channels": [
    {
      "name": "email",
      "enabled": true,
      "rate_limit": 100,
      "tokens_available": 45,
      "sender": "notifications@example.com"
    },
    {
      "name": "telegram",
      "enabled": true,
      "rate_limit": 30,
      "tokens_available": 28,
      "chat_id": "123456789"
    }
  ],
  "timestamp": "2025-11-27T14:30:45Z"
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "unified-notification-service",
  "version": "0.1.0",
  "timestamp": "2025-11-27T14:30:45Z",
  "channels": {
    "email": "ok",
    "telegram": "ok"
  },
  "database": "ok"
}
```

## Pydantic Models

```python
# Requests
class NotificationRequest(BaseModel):
    analysis_id: str
    report_id: str
    channels: List[str]  # ['email', 'telegram']
    recipients: Dict[str, str]  # {'email': 'user@example.com', 'telegram': '123456789'}
    message_type: str = 'summary'  # 'summary', 'alert', 'detailed_report'

    @field_validator('channels')
    def validate_channels(cls, v):
        valid_channels = {'email', 'telegram', 'sms', 'slack', 'discord'}
        if not all(c in valid_channels for c in v):
            raise ValueError(f'Invalid channel(s). Valid: {valid_channels}')
        return v

class NotificationBatchRequest(BaseModel):
    notifications: List[NotificationRequest]

# Responses
class NotificationSuccessResponse(BaseModel):
    request_id: str
    status: str  # 'processing', 'sent', 'failed'
    notification_ids: List[str]
    timestamp: datetime
    channels_created: Dict[str, str]  # {'email': 'success', 'telegram': 'success'}
    duration_ms: int

class NotificationErrorResponse(BaseModel):
    request_id: str
    error: str
    error_code: str
    affected_channels: List[str]
    timestamp: datetime

class DeliveryStatusResponse(BaseModel):
    notification_id: str
    analysis_id: str
    channel: str
    recipient: str  # masked in response
    status: str
    sent_at: Optional[datetime]
    latency_ms: Optional[int]
    external_id: Optional[str]
    retry_count: int
    created_at: datetime

class HealthCheckResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
    channels: Dict[str, str]  # {'email': 'ok', 'telegram': 'ok'}
    database: str
```

## Database Schema

### notifications table

Already defined in PostgreSQL schema specification. Key columns:
- `id UUID PRIMARY KEY`
- `analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE`
- `channel notification_channel` (enum: telegram, email, sms, slack, discord, webhook)
- `recipient TEXT` (email address, chat ID, phone number, etc.)
- `status notification_status` (enum: pending, sent, failed, retrying)
- `sent_at TIMESTAMPTZ`
- `retry_count INTEGER DEFAULT 0`
- `max_retries INTEGER DEFAULT 3`
- `message_id TEXT` (external ID: email Message-ID or Telegram message_id)
- `message_content TEXT` (full message for audit)
- `error_message TEXT` (failure reason if status = failed)
- `metadata JSONB` (delivery_latency_ms, failure_reason, retry_schedule)
- `created_at TIMESTAMPTZ DEFAULT NOW()`
- `updated_at TIMESTAMPTZ DEFAULT NOW()` (auto-updated via trigger)

### notifications_delivery_log table (NEW)

Append-only audit trail for all delivery attempts.

```sql
CREATE TABLE notifications_delivery_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    channel notification_channel NOT NULL,
    recipient TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'sent', 'failed', 'rate_limited'
    sent_at TIMESTAMPTZ,
    latency_ms INTEGER,
    external_id TEXT,
    error_code VARCHAR(50),
    error_message TEXT,
    retry_after_seconds INTEGER,  -- For rate limiting
    metadata JSONB DEFAULT '{}',  -- Additional delivery context
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_delivery_log_notification_id ON notifications_delivery_log(notification_id);
CREATE INDEX idx_delivery_log_channel ON notifications_delivery_log(channel);
CREATE INDEX idx_delivery_log_created_at ON notifications_delivery_log(created_at DESC);
CREATE INDEX idx_delivery_log_status ON notifications_delivery_log(status);
```

### channel_configurations table (NEW)

Runtime channel configuration (enable/disable, rate limits, etc.).

```sql
CREATE TABLE channel_configurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_name VARCHAR(50) NOT NULL UNIQUE,  -- 'email', 'telegram', 'sms', etc.
    is_enabled BOOLEAN DEFAULT true,
    setting_key VARCHAR(100) NOT NULL,  -- 'rate_limit_per_hour', 'timeout_seconds', etc.
    setting_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_channel_config_unique ON channel_configurations(channel_name, setting_key);

-- Example data
INSERT INTO channel_configurations (channel_name, setting_key, setting_value, description) VALUES
  ('email', 'rate_limit_per_hour', '100', 'Max emails per hour'),
  ('email', 'smtp_timeout_seconds', '10', 'SMTP connection timeout'),
  ('telegram', 'rate_limit_per_minute', '30', 'Max Telegram messages per minute'),
  ('telegram', 'api_timeout_seconds', '5', 'Telegram API timeout');
```

## Template System

### Template Directory Structure

```
services/notification-service/
├── templates/
│   ├── email/
│   │   ├── summary.jinja2          # Email with analysis summary
│   │   ├── alert.jinja2            # Quick alert email
│   │   └── detailed_report.jinja2  # Full report email
│   ├── telegram/
│   │   ├── summary.jinja2          # Telegram summary message
│   │   ├── alert.jinja2            # Telegram quick alert
│   │   └── detailed_report.jinja2  # Telegram multi-message report
│   └── shared/
│       ├── macros.jinja2           # Shared macros for formatting
│       └── styles.css              # CSS for HTML email
```

### Template Variables

Base variables passed to all templates:
```python
{
    'report_title': str,
    'report_id': str,
    'summary': str,
    'sentiment': str,  # 'bullish', 'bearish', 'neutral', 'mixed'
    'confidence_score': float,  # 0.0-1.0
    'trading_signals': List[TradingSignal],  # [{action, symbol, entry, target, confidence}, ...]
    'market_insights': List[str],
    'symbols_mentioned': List[str],
    'price_targets': Dict[str, float],
    'report_url': str,
    'timestamp': datetime,
    'ai_provider': str,  # 'anthropic', 'groq'
    'win_rate': Optional[float],
    'profit_loss': Optional[float],
}
```

### Example Email Template (email/summary.jinja2)

```jinja2
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .signal { background: #f5f5f5; padding: 10px; margin: 10px 0; border-left: 4px solid #007bff; }
        .bullish { border-left-color: #28a745; }
        .bearish { border-left-color: #dc3545; }
        .neutral { border-left-color: #6c757d; }
        .metric { display: inline-block; margin: 5px 10px 5px 0; }
        .footer { font-size: 12px; color: #666; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>{{ report_title }}</h2>

        <div class="metric">
            <strong>Sentiment:</strong> {{ sentiment|title }}
        </div>
        <div class="metric">
            <strong>Confidence:</strong> {{ (confidence_score * 100)|int }}%
        </div>
        {% if win_rate %}<div class="metric">
            <strong>Win Rate:</strong> {{ win_rate|round(1) }}%
        </div>{% endif %}

        <p>{{ summary }}</p>

        {% if trading_signals %}
        <h3>Trading Signals</h3>
        {% for signal in trading_signals %}
        <div class="signal {{ signal.action|lower }}">
            <strong>{{ signal.action }}</strong> {{ signal.symbol }}
            {% if signal.entry_price %}<br/>Entry: ${{ signal.entry_price|round(2) }}{% endif %}
            {% if signal.target_price %}<br/>Target: ${{ signal.target_price|round(2) }}{% endif %}
            <br/>Confidence: {{ (signal.confidence_score * 100)|int }}%
        </div>
        {% endfor %}
        {% endif %}

        <div class="footer">
            <p><a href="{{ report_url }}">View Full Report</a></p>
            <p>Generated: {{ timestamp|datetimeformat('%Y-%m-%d %H:%M:%S') }}</p>
            <p>Analysis: {{ ai_provider|title }}</p>
        </div>
    </div>
</body>
</html>
```

### Example Telegram Template (telegram/summary.jinja2)

```jinja2
📊 *{{ report_title }}*

*Sentiment:* {{ sentiment|title }} ({{ (confidence_score * 100)|int }}%)
{% if win_rate %}*Win Rate:* {{ win_rate|round(1) }}%{% endif %}

{{ summary }}

{% if trading_signals %}
*Trading Signals:*
{% for signal in trading_signals %}
• {{ signal.action }} {{ signal.symbol }} {% if signal.entry_price %}@{{ signal.entry_price|round(2) }}{% endif %} → {{ signal.target_price|round(2) if signal.target_price else '?' }} ({{ (signal.confidence_score * 100)|int }}%)
{% endfor %}
{% endif %}

🔗 [Full Report]({{ report_url }})
📝 _{{ ai_provider|title }} Analysis_
```

## Implementation Tasks

### Phase 1: Core Service Structure
1. Create FastAPI app skeleton with lifespan management
2. Implement config management (environment variables + database)
3. Create base Channel abstract class
4. Implement ChannelFactory for channel instantiation
5. Set up database connection pool and async context managers
6. Implement health check endpoint

### Phase 2: Channel Implementations
1. Implement EmailChannel with SMTP integration
2. Implement TelegramChannel with Bot API integration
3. Create Jinja2 template system with validation
4. Implement TokenBucket rate limiter per channel
5. Add request/response Pydantic models
6. Implement /api/v1/notify endpoint (basic send)

### Phase 3: Retry & Resilience
1. Implement exponential backoff retry logic
2. Create retry queue and scheduler
3. Implement notifications_delivery_log table
4. Add retry-eligible query with backoff calculation
5. Add rate limiting integration to send flow
6. Implement /api/v1/delivery-status endpoint

### Phase 4: Monitoring & Audit
1. Implement /api/v1/delivery-stats endpoint
2. Add system_logs entries for delivery events
3. Implement channel health check
4. Add /api/v1/channels status endpoint
5. Create monitoring dashboard queries
6. Implement error alerting to operator

### Phase 5: Advanced Features
1. Implement /api/v1/notify/batch endpoint
2. Add message template variants (alert, detailed_report)
3. Implement dynamic channel enable/disable
4. Add channel configuration hot-reload
5. Implement retry strategy customization per channel
6. Add A/B testing support for templates

## Configuration & Environment Variables

### Required Environment Variables

```bash
# Service Configuration
SERVICE_PORT=8003
LOG_LEVEL=INFO
SERVICE_NAME=notification-service

# Database
DATABASE_URL=postgresql://trading_user:password@localhost:5432/trading_reports
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10

# Email Channel (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=notifications@example.com
SMTP_PASSWORD=your-app-specific-password
SENDER_EMAIL=notifications@example.com

# Telegram Channel
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789  # Default chat ID (can override per request)

# Optional: SMS Channel (Phase 2)
SMS_PROVIDER=twilio  # or vonage, AWS SNS, etc.
SMS_API_KEY=your-api-key
SMS_SENDER_ID=YourSenderID

# Service-to-Service Communication
CORRELATION_ID_HEADER=X-Correlation-ID
```

### Optional Configuration (Database Overrides)

Channel settings in database override environment defaults:
- rate_limit_per_hour (default from env, can customize per channel)
- timeout_seconds (how long to wait for external API)
- retry_max_attempts (default 5, can customize)
- retry_backoff_base (default 2, for 2^n backoff)

## Integration Points

### From N8N Workflow

N8N triggers notification service when analysis is complete:

```javascript
// N8N HTTP Request node
{
  method: 'POST',
  url: 'http://notification-service:8003/api/v1/notify',
  headers: {
    'Content-Type': 'application/json',
    'X-Correlation-ID': '{{ $json.correlation_id }}'
  },
  body: {
    analysis_id: '{{ $json.analysis_id }}',
    report_id: '{{ $json.report_id }}',
    channels: ['email', 'telegram'],
    recipients: {
      email: 'trader@example.com',
      telegram: '123456789'
    },
    message_type: 'summary'
  }
}
```

### From AI Analyzer Service

AI Analyzer publishes analysis result; N8N picks up and triggers notification service:

```
AI Analyzer Service
  └─> Insert into analyses table
       └─> Trigger: system_logs entry created
            └─> N8N poller detects new analysis
                 └─> Call notification-service webhook
```

### Database Event Flow

```
1. analyses table INSERT (new analysis created)
   └─> Trigger: insert into system_logs (analysis_completed event)
        └─> N8N polling query detects change
             └─> POST /api/v1/notify to notification-service

2. notification-service creates notifications records
   └─> notifications table INSERT (one per channel: email, telegram)
        └─> Each notification: status='pending'
             └─> Return notification_ids to N8N

3. notification-service async background worker
   └─> Find pending/retrying notifications
        └─> For each: render template → send → update status
             └─> Insert into notifications_delivery_log (audit trail)
                  └─> Update notifications record (status='sent' or 'failed')
```

## Testing Strategy

### Unit Tests

Test individual components in isolation with mocks:

```python
# tests/test_channels/test_email_channel.py
def test_email_validation():
    channel = EmailChannel({})
    assert channel.validate_recipient('user@example.com') == True
    assert channel.validate_recipient('invalid-email') == False

def test_email_rate_limiting():
    bucket = TokenBucket(capacity=100, refill_rate=100/3600)
    assert await bucket.try_consume(1) == True
    # Mock time advancement...
    assert await bucket.try_consume(200) == False

# tests/test_services/test_notification_service.py
@mock.patch('aiosmtplib.SMTP.send_message')
async def test_send_email_success(mock_smtp):
    service = NotificationService()
    result = await service.send(notification_request)
    assert result['success'] == True
    mock_smtp.assert_called_once()
```

### Integration Tests

Test service integration with mocked external APIs:

```python
# tests/test_integration/test_notify_endpoint.py
@pytest.mark.asyncio
async def test_notify_endpoint_success(client, mocker):
    # Mock SMTP send
    mocker.patch('aiosmtplib.SMTP.send_message', return_value='msg-id')
    # Mock Telegram API
    mocker.patch('requests.post', return_value=MockResponse(ok=True))

    response = await client.post('/api/v1/notify', json={
        'analysis_id': 'uuid1',
        'report_id': 'uuid2',
        'channels': ['email', 'telegram'],
        'recipients': {'email': 'user@example.com', 'telegram': '123456789'}
    })

    assert response.status_code == 202
    assert len(response.json()['notification_ids']) == 2
```

### End-to-End Tests

Test complete flow with real database and external APIs (staging only):

```bash
# In staging environment with real SMTP server and Telegram bot
pytest tests/test_e2e/test_full_flow.py -v
```

### Database Transaction Tests

Test database consistency and retry logic:

```python
# tests/test_database/test_retry_logic.py
@pytest.mark.asyncio
async def test_notification_retry_on_failure():
    # Create pending notification
    await db.insert_notification(...)

    # Simulate send failure
    with mock.patch('aiosmtplib') as mock_smtp:
        mock_smtp.side_effect = SMTPException()
        await notification_service.send(notif)

    # Verify status='retrying' and retry_count=1
    notif = await db.get_notification(id)
    assert notif.status == 'retrying'
    assert notif.retry_count == 1
```

### Rate Limiting Tests

Test token bucket and 429 responses:

```python
# tests/test_rate_limiting.py
@pytest.mark.asyncio
async def test_rate_limit_429():
    channel = EmailChannel(config={'rate_limit_per_hour': 10})
    channel.rate_limiter = TokenBucket(capacity=10, refill_rate=10/3600)

    # Consume all tokens
    for _ in range(10):
        assert await channel.check_rate_limit() == True

    # Next request should fail
    response = await notify_endpoint(request)
    assert response.status_code == 429
    assert response.json()['error_code'] == 'RATE_LIMIT_EXCEEDED'
```

## Deployment & Operations

### Docker Container Setup

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY services/notification-service ./

# Create non-root user
RUN useradd -m -u 1000 notif && chown -R notif:notif /app
USER notif

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8003/health')"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8003"]
```

### Docker Compose Integration

```yaml
services:
  notification-service:
    build: ./services/notification-service
    container_name: trading-notification
    ports:
      - "8003:8003"
    environment:
      - SERVICE_PORT=8003
      - LOG_LEVEL=INFO
      - DATABASE_URL=postgresql://trading_user:${POSTGRES_PASSWORD}@postgres:5432/trading_reports
      - SMTP_HOST=smtp.gmail.com
      - SMTP_USER=${GMAIL_USER}
      - SMTP_PASSWORD=${GMAIL_APP_PASSWORD}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - trading
    restart: unless-stopped
```

### Health Check Endpoints

```python
@app.get("/health")
async def health_check():
    """
    Health check returning service and channel status.

    Returns 200 OK if all critical components healthy.
    Returns 503 Service Unavailable if database unreachable.
    """
    db_healthy = await check_db_connection()
    channels_status = {
        'email': 'ok' if email_channel.is_configured() else 'disabled',
        'telegram': 'ok' if telegram_channel.is_configured() else 'disabled'
    }

    overall_status = 'ok' if db_healthy else 'error'
    status_code = 200 if db_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            'status': overall_status,
            'service': 'unified-notification-service',
            'version': '0.1.0',
            'timestamp': datetime.utcnow().isoformat(),
            'channels': channels_status,
            'database': 'ok' if db_healthy else 'error'
        }
    )
```

### Monitoring & Alerting

Key metrics to track:
- Delivery success rate per channel (target: >99%)
- Average delivery latency (email <10s, telegram <5s)
- Retry rate (target: <2% of notifications)
- Rate limit occurrences (should be 0 under normal load)
- Database connection pool utilization
- Failed deliveries requiring manual intervention

### Debugging Commands

```bash
# View service logs
docker-compose logs -f notification-service

# Check service health
curl http://localhost:8003/health

# Query notification status
psql -U trading_user -d trading_reports -c "
  SELECT id, channel, status, retry_count, error_message
  FROM notifications
  WHERE created_at > NOW() - INTERVAL '1 hour'
  ORDER BY created_at DESC;"

# Check rate limiting status
psql -U trading_user -d trading_reports -c "
  SELECT channel_name, setting_key, setting_value
  FROM channel_configurations;"

# Find failed notifications needing retry
psql -U trading_user -d trading_reports -c "
  SELECT id, channel, recipient, retry_count, error_message
  FROM notifications
  WHERE status = 'failed' AND retry_count < max_retries;"

# Monitor delivery latency
psql -U trading_user -d trading_reports -c "
  SELECT channel, COUNT(*) as count, AVG(metadata->>'delivery_latency_ms') as avg_latency_ms
  FROM notifications
  WHERE created_at > NOW() - INTERVAL '24 hours' AND status = 'sent'
  GROUP BY channel;"
```

### Rollback Strategy

1. **Gradual Rollback**: Update N8N workflow to send notifications to old separate services instead of unified service
2. **Database Compatibility**: notifications table structure remains compatible with old services
3. **Data Preservation**: All delivery logs in notifications_delivery_log remain for audit
4. **No Data Loss**: Notifications sent via unified service are already recorded; no resending needed
5. **Monitoring**: Watch delivery success rates during transition back to old services

## Migration Strategy

### Phase 1: Parallel Deployment
- Deploy unified notification service alongside old email and Telegram services
- N8N continues sending to old services (no change)
- New code paths tested in isolation

### Phase 2: Canary Testing
- Route 10% of notifications to unified service via N8N conditional split
- Monitor success rates and latencies
- Gradually increase percentage (10% → 25% → 50% → 100%)

### Phase 3: Full Cutover
- Update N8N workflow to send all notifications to unified service
- Keep old services running for rollback (48+ hours)
- Monitor closely for failures or latency issues

### Phase 4: Cleanup
- Decommission old email and Telegram notification services
- Archive old service code in git branches
- Keep rollback plan documented for future reference

### Database Backward Compatibility
- Unified service uses existing notifications table (no schema changes required)
- Old services can read/write same table during parallel operation
- notifications_delivery_log is append-only, safe for parallel writers
- No locking issues: separate notification records per service invocation

## Future Extensibility Examples

### Adding SMS Channel (Phase 2)

```python
class SMSChannel(Channel):
    """SMS delivery via Twilio or similar provider."""

    async def send(self, message: str, recipient: str) -> Dict[str, Any]:
        # Render SMS template (shorter, plain text)
        # Call SMS API
        # Return result with external SID
        pass

    def validate_recipient(self, recipient: str) -> bool:
        # Validate phone number format
        pass
```

Update database:
```sql
-- Update notification_channel enum
ALTER TYPE notification_channel ADD VALUE 'sms' BEFORE 'slack';

-- Add SMS configuration
INSERT INTO channel_configurations (channel_name, setting_key, setting_value) VALUES
  ('sms', 'rate_limit_per_hour', '50'),
  ('sms', 'provider', 'twilio'),
  ('sms', 'api_timeout_seconds', '8');

-- Create SMS template
-- services/notification-service/templates/sms/summary.jinja2
```

No code changes to core service; just add channel class and register in factory.

### Adding Slack Channel (Phase 3)

```python
class SlackChannel(Channel):
    """Slack messaging via Webhook or Bot API."""

    async def send(self, message: str, recipient: str) -> Dict[str, Any]:
        # recipient = Slack channel ID or user ID
        # Send via Slack API with formatted blocks
        # Return result with Slack message timestamp
        pass
```

Same process: add channel class, register, create templates.

## Security Considerations

### Credential Management
- SMTP passwords, Telegram tokens, SMS API keys stored in `.env` only
- Never log full credentials; log only provider name and last 4 chars
- Support credential rotation by updating environment variable (no restart required)
- Validate credentials during service startup (fail fast)

### Message Content Sanitization
- Remove embedded credentials/secrets from message before sending
- Sanitize URLs to prevent injection attacks
- Validate template content doesn't contain malicious scripts
- HTML emails: strip dangerous tags (script, iframe, etc.)

### Recipient Validation
- Validate email addresses, phone numbers, chat IDs before sending
- Prevent sending to unvalidated/unconfirmed recipients
- Log all send attempts with masked recipient (audit trail)

### Rate Limiting
- Prevent abuse/spam: rate limit per channel and globally
- Detect anomalies (sudden surge in notifications)
- Alert operator if rate limits consistently hit

### Access Control
- API endpoints should be accessed only from N8N workflow (internal)
- Implement API key authentication if exposed externally
- Use SSL/TLS for all external API calls (SMTP, Telegram, SMS)

## Summary

The Unified Notification Service consolidates email and Telegram delivery into a single, extensible, production-ready service with:

- **Modular architecture** via factory pattern and pluggable channels
- **Reliable delivery** with database-backed retries and exponential backoff
- **Rate limiting** per channel to prevent abuse and external API throttling
- **Complete audit trail** with append-only delivery logs and system events
- **Configuration flexibility** with environment variables and runtime database settings
- **Easy extensibility** for new channels (SMS, Slack, Discord) without core changes
- **Production operations** with health checks, monitoring, and debugging tools
- **Clear migration path** from two separate services with zero data loss
