# Unified Notification Service

A production-ready FastAPI microservice for sending notifications via email and Telegram channels with built-in retry logic, rate limiting, and complete audit trails.

## Overview

The Unified Notification Service consolidates email and Telegram notification delivery into a single, extensible service. It provides:

- Multi-channel notification delivery (Email via SMTP, Telegram via Bot API)
- Database-backed retry mechanism with exponential backoff (1s, 2s, 4s, 8s...)
- Per-channel token bucket rate limiting (100 emails/hour, 30 messages/minute)
- Complete audit trail with append-only delivery logs
- Jinja2 template system with multiple message variants
- Credential masking in all logs and responses
- Health check and monitoring endpoints

## Architecture

```
FastAPI HTTP Layer
    ├─ POST /api/v1/notify
    ├─ GET /api/v1/delivery-status/{id}
    ├─ GET /api/v1/delivery-stats
    └─ GET /api/v1/channels

NotificationService (Orchestration)
    ├─ Message rendering (Jinja2)
    ├─ Channel selection
    ├─ Rate limiting
    └─ Database transaction management

ChannelFactory
    ├─ EmailChannel (SMTP)
    ├─ TelegramChannel (Bot API)
    └─ (Future: SMS, Slack, Discord)

Database
    ├─ notifications (status tracking)
    ├─ notifications_delivery_log (audit trail)
    └─ channel_configurations (runtime config)
```

## Quick Start

### 1. Installation

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SENDER_EMAIL`: Email configuration
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: Telegram configuration

### 3. Run Service

```bash
# Development mode
uvicorn src.main:app --reload

# Production mode
uvicorn src.main:app --host 0.0.0.0 --port 8003
```

### 4. Docker Deployment

```bash
# Build image
docker build -t notification-service:latest .

# Run container
docker run -d \
  --name notification-service \
  --env-file .env \
  -p 8003:8003 \
  notification-service:latest
```

## API Endpoints

### POST /api/v1/notify

Send notification(s) to specified channels.

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

**Response (202 Accepted):**
```json
{
  "request_id": "uuid",
  "status": "processing",
  "notification_ids": ["notif-id-1", "notif-id-2"],
  "timestamp": "2025-11-27T14:30:45Z",
  "channels_created": {"email": "success", "telegram": "success"},
  "duration_ms": 45
}
```

### GET /api/v1/delivery-status/{notification_id}

Get delivery status of a notification.

**Response:**
```json
{
  "notification_id": "uuid",
  "channel": "email",
  "recipient": "u***@example.com",
  "status": "sent",
  "sent_at": "2025-11-27T14:30:52Z",
  "latency_ms": 7250,
  "retry_count": 0
}
```

### GET /api/v1/delivery-stats?period_days=7

Get aggregated delivery statistics.

**Response:**
```json
{
  "period_days": 7,
  "total_notifications": 150,
  "by_channel": {
    "email": {
      "total": 100,
      "sent": 98,
      "success_rate": 98.0,
      "avg_latency_ms": 5234
    }
  },
  "avg_retries": 0.35
}
```

### GET /api/v1/channels

List enabled channels and their status.

**Response:**
```json
{
  "channels": [
    {
      "name": "email",
      "enabled": true,
      "rate_limit": 100,
      "tokens_available": 45
    }
  ],
  "timestamp": "2025-11-27T14:30:45Z"
}
```

### GET /health

Health check endpoint.

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_channels.py

# Run with coverage
pytest --cov=src
```

## Monitoring

### Key Metrics

- **Delivery Success Rate**: Goal >99%
- **Average Latency**: Email <10s, Telegram <5s
- **Retry Rate**: Goal <2% of notifications
- **Rate Limit Hits**: Should be 0 under normal load

### Database Queries

Check notification status:
```sql
SELECT id, channel, status, retry_count, created_at
FROM notifications
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

View delivery logs:
```sql
SELECT notification_id, channel, status, latency_ms, error_code
FROM notifications_delivery_log
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

Monitor rate limiting:
```sql
SELECT channel_name, setting_key, setting_value
FROM channel_configurations
WHERE setting_key LIKE '%rate_limit%';
```

## Configuration Management

### Environment Variables (Secrets)

Set in `.env` file:
- Database credentials
- SMTP password
- Telegram bot token
- API keys

### Database Configuration (Settings)

Configure via database:
```sql
INSERT INTO channel_configurations (channel_name, setting_key, setting_value)
VALUES ('email', 'rate_limit_per_hour', '200');
```

Settings are reloaded periodically without service restart.

## Troubleshooting

### Service Won't Start

```bash
# Check database connection
psql postgresql://user:password@localhost/trading_reports

# Check environment variables
cat .env

# View service logs
docker logs notification-service
```

### Email Delivery Fails

```sql
SELECT * FROM notifications_delivery_log
WHERE channel = 'email' AND status = 'failed'
ORDER BY created_at DESC LIMIT 5;
```

Common issues:
- SMTP credentials invalid
- SENDER_EMAIL not configured
- SMTP server requires TLS/SSL

### Telegram Delivery Fails

```sql
SELECT * FROM notifications_delivery_log
WHERE channel = 'telegram' AND status = 'failed'
ORDER BY created_at DESC LIMIT 5;
```

Common issues:
- Bot token invalid or expired
- Chat ID doesn't exist
- Bot not added to chat

## Development

### Project Structure

```
services/notification-service/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic request/response models
│   ├── api/routes.py        # API endpoints
│   ├── channels/            # Channel implementations
│   ├── services/            # Business logic
│   ├── db/                  # Database access
│   ├── templates/           # Jinja2 templates
│   └── utils/               # Utilities (logging, masking, etc.)
├── tests/                   # Unit and integration tests
├── Dockerfile
├── requirements.txt
└── README.md
```

### Code Standards

- Follow PEP 8 style guide
- Use type hints for all functions
- Add docstrings to public methods
- Write focused unit tests
- Mask sensitive data in logs

### Adding a New Channel

1. Create channel class extending `Channel`:
```python
class SMSChannel(Channel):
    async def send(self, message: str, recipient: str) -> Dict[str, Any]:
        # Implementation
        pass
```

2. Register in `ChannelFactory._instantiate_channel()`
3. Create message templates in `templates/sms/`
4. Configure in database:
```sql
INSERT INTO channel_configurations (channel_name, setting_key, setting_value)
VALUES ('sms', 'rate_limit_per_hour', '100');
```

## Performance Tuning

### Database Connection Pool

Adjust in `.env`:
```bash
DATABASE_POOL_MIN=5      # Minimum connections
DATABASE_POOL_MAX=20     # Maximum connections
```

### Rate Limiting

Adjust per channel:
```sql
UPDATE channel_configurations
SET setting_value = '200'
WHERE channel_name = 'email' AND setting_key = 'rate_limit_per_hour';
```

### Retry Settings

```sql
UPDATE channel_configurations
SET setting_value = '10'
WHERE setting_key = 'max_retries';
```

## License

Proprietary - Trading Report Monitor

## Support

For issues or questions, contact the development team.
