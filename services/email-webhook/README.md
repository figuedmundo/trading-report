# Email Webhook Service

HTTP webhook endpoint for receiving trading report notifications from email service providers (Mailgun, SendGrid, etc.). This is the entry point to the trading report automation pipeline.

## Overview

The Email Webhook Service:
- Receives email payloads from external email service providers via secure HTTPS webhooks
- Validates webhook requests using HMAC-SHA256 signatures and API key authentication
- Extracts and parses email metadata (From, Subject, Message-ID, Date, etc.)
- Detects trading reports using configurable keyword matching
- Extracts URLs pointing to trading portals with domain/path filtering
- Stores normalized email metadata in PostgreSQL for downstream processing
- Provides comprehensive audit logging and error handling

## Architecture

```
Email Provider (Mailgun/SendGrid)
    ↓
Webhook POST /webhook/email
    ↓
HMAC-SHA256 Signature Verification
    ↓
Email Parsing (headers, body, MIME)
    ↓
Keyword Detection (Trading Report)
    ↓
URL Extraction & Validation
    ↓
PostgreSQL reports table
    ↓
N8N Workflow Orchestration
    ↓
Downstream: Scraper, Analyzer, Notification Services
```

## Setup & Configuration

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- pip for package management

### Installation

1. **Clone the repository:**
   ```bash
   cd services/email-webhook
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | | PostgreSQL connection string: `postgresql://user:password@host:5432/database` |
| `WEBHOOK_SIGNATURE_SECRET` | Yes | | HMAC-SHA256 shared secret (base64 encoded) |
| `API_KEY_FALLBACK` | No | | Optional API key for fallback authentication |
| `REPORT_KEYWORDS` | No | trading report,analysis,recommendation,trade alert | Keywords for trading report detection (comma-separated) |
| `TRUSTED_DOMAINS` | No | protradingskills.com | Trusted portal domains for URL filtering |
| `RATE_LIMIT_PER_SECOND` | No | 1 | Per-sender rate limit (requests per second) |
| `RATE_LIMIT_PER_HOUR` | No | 100 | Global rate limit (requests per hour) |
| `LOG_LEVEL` | No | INFO | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

### Generate Secret Key

```bash
# Generate HMAC-SHA256 secret
openssl rand -base64 32
```

## API Documentation

### POST /webhook/email

Receive email payload from email service provider.

**Request Headers:**
```
Content-Type: application/json
X-Signature: <HMAC-SHA256 hex> (for Mailgun)
X-API-Key: <api-key> (alternative authentication)
```

**Request Body (Mailgun format):**
```json
{
  "from": "sender@example.com",
  "subject": "Trading Report - Nov 25",
  "stripped-text": "Report content here...",
  "timestamp": "Mon, 25 Nov 2025 10:00:00 +0000",
  "message-id": "<msg-123@example.com>",
  "to": "receive@example.com",
  "cc": "cc@example.com"
}
```

**Request Body (SendGrid format):**
```json
{
  "from": "sender@example.com",
  "subject": "Trading Report - Nov 25",
  "text": "Report content here...",
  "timestamp": "1732516800",
  "message_id": "msg-123@example.com",
  "to": "receive@example.com"
}
```

**Success Response (201 Created - New Report):**
```json
{
  "success": true,
  "status": "created",
  "report_id": "123e4567-e89b-12d3-a456-426614174000",
  "correlation_id": "456f7890-abcd-ef12-3456-789012345678",
  "message": "Email processed successfully",
  "timestamp": "2025-11-25T10:00:00Z"
}
```

**Success Response (202 Accepted - Duplicate/No URLs):**
```json
{
  "success": true,
  "status": "accepted",
  "report_id": "123e4567-e89b-12d3-a456-426614174000",
  "correlation_id": "456f7890-abcd-ef12-3456-789012345678",
  "message": "Email processed successfully",
  "timestamp": "2025-11-25T10:00:00Z"
}
```

**Error Response (401 Unauthorized):**
```json
{
  "success": false,
  "status": "rejected",
  "error": "Signature verification failed",
  "correlation_id": "456f7890-abcd-ef12-3456-789012345678",
  "timestamp": "2025-11-25T10:00:00Z"
}
```

**Status Codes:**
- `201 Created`: New report successfully created and stored
- `202 Accepted`: Valid email received (may be duplicate or no valid URLs)
- `400 Bad Request`: Malformed JSON, missing required fields
- `401 Unauthorized`: Signature/API key verification failed
- `429 Too Many Requests`: Rate limit exceeded (see `Retry-After` header)
- `500 Internal Server Error`: Database error or unexpected exception

### GET /health

Health check endpoint for service monitoring.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-11-25T10:00:00Z",
  "database": "connected"
}
```

**Status Codes:**
- `200 OK`: Service healthy, database connected
- `503 Service Unavailable`: Database unreachable

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_security.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

### Test Organization

- `test_infrastructure.py`: FastAPI initialization, health check
- `test_database.py`: Database connectivity and pooling
- `test_security.py`: HMAC-SHA256 signature verification, API key auth
- `test_parsing.py`: Email header extraction, multipart MIME handling
- `test_detection.py`: Keyword-based report detection
- `test_extraction.py`: URL extraction and portal filtering
- `test_storage.py`: Database report insertion, deduplication
- `test_response_format.py`: Response schema validation
- `test_rate_limiting.py`: Rate limit configuration
- `test_error_handling.py`: Error logging

## Deployment

### Docker

Build and run with Docker:

```bash
# Build image
docker build -t email-webhook:latest .

# Run container
docker run -p 8001:8001 --env-file .env email-webhook:latest
```

### Docker Compose

Included in main `docker-compose.yml`:

```bash
docker-compose up email-webhook
```

## Configuration for Email Providers

### Mailgun

1. Go to Mailgun Dashboard → Webhooks
2. Set webhook URL: `https://your-domain/webhook/email`
3. Signature secret: Use `WEBHOOK_SIGNATURE_SECRET` from environment
4. Select events: Message Delivery, Message Click, Message Open, etc.

### SendGrid

1. Go to SendGrid Dashboard → Settings → Event Webhook
2. Set webhook URL: `https://your-domain/webhook/email`
3. Use `X-API-Key` header if signature verification unavailable
4. Select events: Delivered, Bounce, Click, Open, etc.

## Troubleshooting

### Connection Refused
```
Error: Failed to initialize connection pool: connection refused
```
**Solution:** Verify PostgreSQL is running and `DATABASE_URL` is correct.

### Signature Verification Failed
```
{"success": false, "status": "rejected", "error": "Signature verification failed"}
```
**Solution:** Ensure `WEBHOOK_SIGNATURE_SECRET` matches the secret configured in your email provider.

### Rate Limit Exceeded
```
{"success": false, "status": "rejected", "error": "Rate limit exceeded"}
```
**Solution:** Rate limits are per-sender (1 req/sec) and global (100 req/hour). Wait before retrying.

### Database Error
Check logs with:
```bash
docker-compose logs email-webhook
```

## Performance

- Webhook processing: < 500ms per request
- Database write: Optimized with connection pooling
- Signature verification: Constant-time comparison
- Keywords matching: Case-insensitive word boundary matching

## Security

- HMAC-SHA256 signature verification mandatory
- Rate limiting prevents abuse (per-sender and global)
- Parameterized queries prevent SQL injection
- Generic error messages (no technical details exposed)
- Full audit trail in system_logs table
- Correlation IDs for request tracing

## Monitoring

Health check endpoint for orchestration:
```bash
curl http://localhost:8001/health
```

Logs available in:
- PostgreSQL `system_logs` table
- Docker logs: `docker-compose logs email-webhook`

## Development

### Code Structure

```
src/
├── main.py           # FastAPI app, webhook endpoint
├── config.py         # Environment configuration
├── models.py         # Pydantic request/response models
├── security.py       # HMAC-SHA256 signature verification
├── parsers.py        # Email header and body parsing
├── detection.py      # Keyword-based report detection
├── extractors.py     # URL extraction and validation
├── storage.py        # Database report insertion
├── database.py       # PostgreSQL connection pooling
└── system_logging.py # Structured logging to system_logs
```

### Standards Compliance

All code follows project standards:
- **Coding Style**: `agent-os/standards/global/coding-style.md`
- **API Design**: `agent-os/standards/backend/api.md`
- **Models**: `agent-os/standards/backend/models.md`
- **Error Handling**: `agent-os/standards/global/error-handling.md`
- **Validation**: `agent-os/standards/global/validation.md`

## License

Trading Report Monitor - Automated Trading Report Ingestion System

## Support

For issues or questions, see:
- Project: `/agent-os/specs/2025-11-25-email-webhook-service/`
- Tech Stack: `/agent-os/product/tech-stack.md`
- Architecture: `/CLAUDE.md`
