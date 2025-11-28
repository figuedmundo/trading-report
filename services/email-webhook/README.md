# Email Webhook Service

Multi-layered security service for receiving and validating email webhook requests with signature validation, IP whitelisting, and rate limiting.

## Overview

This service acts as the entry point for email notifications from providers like Mailgun and SendGrid. It implements multiple layers of security to protect against unauthorized access and DDoS attacks:

1. **IP Banning** - Rejects IPs with repeated failed authentication attempts
2. **IP Whitelisting** - Only allows requests from configured email provider IP ranges
3. **Rate Limiting** - Enforces per-IP and global request limits
4. **Signature Validation** - Verifies request authenticity using cryptographic signatures

## Configuration

### Required Environment Variables

```bash
# Security: Webhook signing secret
WEBHOOK_SECRET_KEY=your-secret-key-must-be-at-least-32-characters-long

# Database connection
DATABASE_URL=postgresql://user:password@host:5432/trading_reports

# Email provider IP ranges (CIDR notation)
MAILGUN_IP_RANGES=149.72.0.0/16,161.38.0.0/16
SENDGRID_IP_RANGES=168.245.0.0/16,167.89.0.0/16
```

See `.env.example` for all available configuration options.

## API Endpoints

### Health Check
```
GET /health
```
Returns service health status. Exempt from all security middleware.

Response:
```json
{"status": "ok", "service": "email-webhook"}
```

### Webhook Receiver
```
POST /webhook/email
```
Receives and processes email webhook events from configured providers.

Protected by security middleware in order:
1. IP ban check
2. IP whitelist validation
3. Rate limiting
4. Signature validation

Response (on success):
```json
{"status": "received", "event_id": "uuid"}
```

## Security Features

### IP Whitelisting
- Static IP ranges loaded from environment variables at startup
- Dynamic IP allowlist loaded from PostgreSQL with 5-minute cache refresh
- Supports CIDR notation for both IPv4 ranges
- Automatic soft-deletion of IPs without service restart

### Rate Limiting
- Per-IP minute limit: 5 requests/minute (default)
- Per-IP hour limit: 50 requests/hour (default)
- Global hour limit: 100 requests/hour (default)
- Authenticated requests (valid signature) get 5x multiplier
- In-memory storage with automatic TTL cleanup every 60 seconds

### IP Banning
- Automatic banning after 10 failed authentication attempts (configurable)
- 1-hour ban duration (configurable)
- In-memory ban list synced to database every 5 minutes
- Manual unbanning via database UPDATE

### Signature Validation
- Mailgun: HMAC-SHA256(timestamp + token) with timestamp freshness check
- SendGrid: ECDSA signature verification
- Generic: HMAC-SHA256(body) fallback
- Auto-detection of provider from request headers
- Optional bypass via `SIGNATURE_VALIDATION_ENABLED=false` (testing only)

## Database Schema

### ip_allowlist
- `id` (UUID): Primary key
- `ip_address` (VARCHAR 45 UNIQUE): IPv4 or IPv6 address
- `description` (TEXT): Purpose of IP
- `enabled` (BOOLEAN): Soft delete flag
- `created_at`, `updated_at` (TIMESTAMPTZ): Timestamps with auto-update trigger

### security_events
- `id` (UUID): Primary key
- `event_type` (VARCHAR 50): Event classification
- `ip_address` (VARCHAR 45): Source IP
- `endpoint` (VARCHAR 255): API endpoint
- `request_headers` (JSONB): Filtered request headers (sensitive data removed)
- `metadata` (JSONB): Event-specific metadata
- `created_at` (TIMESTAMPTZ): Event timestamp

Indexes:
- `idx_security_events_ip` on ip_address
- `idx_security_events_type` on event_type
- `idx_security_events_created` on created_at DESC
- `idx_security_events_type_created` on (event_type, created_at)

### ip_bans
- `id` (UUID): Primary key
- `ip_address` (VARCHAR 45): Banned IP
- `banned_until` (TIMESTAMPTZ): Ban expiry time
- `reason` (TEXT): Ban reason
- `attempt_count` (INTEGER): Failed attempts before ban
- `created_at` (TIMESTAMPTZ): Ban timestamp

Indexes:
- `idx_ip_bans_ip` on ip_address
- `idx_ip_bans_banned_until` on banned_until

## Testing

Run configuration tests only:
```bash
cd /path/to/services/email-webhook
pytest tests/test_config.py -v
```

Run all tests:
```bash
pytest -v
```

Key test files:
- `tests/test_config.py` - Configuration loading and validation
- `tests/test_db_migrations.py` - Database schema and operations
- `tests/test_ip_allowlist.py` - IP whitelisting and CIDR matching
- `tests/test_rate_limiter.py` - Rate limit enforcement
- `tests/test_signature_validation.py` - Signature verification
- `tests/test_security_logging.py` - Security event logging
- `tests/test_middleware.py` - Middleware stack ordering
- `tests/test_integration.py` - End-to-end workflows

## Deployment

### Docker

Build:
```bash
docker build -t email-webhook:latest .
```

Run:
```bash
docker-compose up email-webhook
```

### Configuration at Startup

The service validates all required configuration on startup and raises an error if:
- `WEBHOOK_SECRET_KEY` is missing or less than 32 characters
- `DATABASE_URL` is not configured
- Rate limit values are not positive integers

## Monitoring

### Logs

All logs are structured JSON output to stdout (Docker-friendly):
```json
{
  "timestamp": "2024-11-27T14:30:45Z",
  "level": "ERROR",
  "service": "email-webhook",
  "message": "IP not whitelisted",
  "ip_address": "203.0.113.42",
  "event_type": "ip_not_whitelisted",
  "endpoint": "/webhook/email"
}
```

### Metrics

HTTP response headers include rate limit metadata:
```
X-RateLimit-Remaining: 4
X-RateLimit-Reset: 1234567890
Retry-After: 30
```

## Troubleshooting

### Service won't start
- Check `WEBHOOK_SECRET_KEY` is set and at least 32 characters
- Verify `DATABASE_URL` is correct and PostgreSQL is running
- Check logs for specific validation errors

### Legitimate requests being blocked
- Verify IP is in `MAILGUN_IP_RANGES` or `SENDGRID_IP_RANGES`
- Check rate limit hasn't been exceeded for the IP
- Ensure signature is valid (if `SIGNATURE_VALIDATION_ENABLED=true`)
- Look for IP in `security_events` table for diagnostics

### High rate of failures
- Check for attack patterns in `security_events` table
- Review IPs in `ip_bans` table
- Verify email provider IP ranges are current

## Performance Considerations

- Connection pool: 5-20 connections (configurable)
- In-memory rate limit storage: ~1KB per active IP
- Security event batch cleanup: Every 60 seconds
- IP allowlist cache refresh: Every 5 minutes (configurable)
- Old security events pruning: Once per day

## Security Notes

- Never commit `.env` file with actual secrets
- Rotate `WEBHOOK_SECRET_KEY` regularly in production
- Monitor `security_events` table for attack patterns
- Keep PostgreSQL backups current for audit trail recovery
- Review IP bans periodically for false positives
