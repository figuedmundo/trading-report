# Credential Service

Secure credential management service for the Trading Report Automation system.

Provides REST API for storing, retrieving, and managing encrypted trading portal credentials with:
- Fernet symmetric encryption (AES-128 CBC + HMAC)
- Audit logging of all credential access
- Per-report credential override support
- Fallback to environment variables for backward compatibility

## Architecture

### Service Overview

```
Client/Scraper
    |
    v
Credential Service API (FastAPI)
    |
    ├─> Encryption/Decryption (cryptography.Fernet)
    |
    └─> PostgreSQL Database
        ├─> credentials table (encrypted storage)
        └─> system_logs table (audit trail)
```

### Key Components

1. **encryption.py** - Fernet-based encryption/decryption with master key from environment
2. **database.py** - Connection pooling and credential CRUD operations
3. **schemas.py** - Pydantic models for request/response validation
4. **main.py** - FastAPI application with REST endpoints
5. **logging_utils.py** - Automatic log sanitization to prevent credential exposure

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 16.1+
- Environment variables configured (see Environment Variables)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:password@localhost:5432/trading_reports"
export CREDENTIAL_ENCRYPTION_KEY="<base64-encoded-32-byte-key>"

# Run the service
python -m src.main
```

## API Endpoints

All endpoints return JSON with correlation_id for distributed tracing.

### Create Credential

```http
POST /api/v1/credentials
Content-Type: application/json

{
    "domain": "broker.com",
    "username": "trader@broker.com",
    "password": "secure_password_123",
    "metadata": {
        "login_url": "https://broker.com/login",
        "2fa_enabled": false
    }
}
```

Response (201 Created):
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "domain": "broker.com",
    "username": "trader@broker.com",
    "is_active": true,
    "metadata": {
        "login_url": "https://broker.com/login",
        "2fa_enabled": false
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "correlation_id": "abc-123-def"
}
```

### Retrieve Credential by Domain

```http
GET /api/v1/credentials/domain/broker.com
```

Response (200 OK):
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "domain": "broker.com",
    "username": "trader@broker.com",
    "password": "secure_password_123",
    "is_active": true,
    "metadata": {
        "login_url": "https://broker.com/login",
        "2fa_enabled": false
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "last_used_at": "2024-01-01T12:00:00Z",
    "correlation_id": "abc-123-def"
}
```

### Retrieve Credential by ID

```http
GET /api/v1/credentials/550e8400-e29b-41d4-a716-446655440000
```

Response (200 OK): Same as retrieve by domain

### Update Credential

```http
PUT /api/v1/credentials/550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
    "domain": "broker.com",
    "username": "newuser@broker.com",
    "password": "new_password_456",
    "metadata": {
        "login_url": "https://broker.com/login",
        "2fa_enabled": true
    }
}
```

Response (200 OK): Updated credential (same format as create)

### Delete Credential

```http
DELETE /api/v1/credentials/550e8400-e29b-41d4-a716-446655440000
```

Response (204 No Content)

### List All Credentials

```http
GET /api/v1/credentials
```

Response (200 OK):
```json
{
    "credentials": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "domain": "broker1.com",
            "username": "user1",
            "is_active": true,
            "metadata": {},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "last_used_at": null
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "domain": "broker2.com",
            "username": "user2",
            "is_active": true,
            "metadata": {},
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "last_used_at": null
        }
    ],
    "total": 2,
    "correlation_id": "abc-123-def"
}
```

### Health Check

```http
GET /health
```

Response (200 OK):
```json
{
    "status": "ok",
    "database_connected": true,
    "timestamp": "2024-01-01T00:00:00Z",
    "correlation_id": "abc-123-def"
}
```

## Error Responses

### 400 Bad Request

Invalid request body or parameters.

```json
{
    "detail": "Invalid domain format"
}
```

### 404 Not Found

Credential or domain not found.

```json
{
    "code": "CREDENTIAL_NOT_FOUND",
    "message": "No active credential found for domain broker.com",
    "correlation_id": "abc-123-def"
}
```

### 409 Conflict

Credential already exists for domain.

```json
{
    "detail": "Credential already exists for domain broker.com"
}
```

### 500 Internal Server Error

Encryption, decryption, or database error.

```json
{
    "code": "DECRYPTION_FAILED",
    "message": "Failed to decrypt credentials for domain broker.com",
    "correlation_id": "abc-123-def"
}
```

## Environment Variables

### Required

- **DATABASE_URL** - PostgreSQL connection string
  - Example: `postgresql://trading_user:password@postgres:5432/trading_reports`

- **CREDENTIAL_ENCRYPTION_KEY** - Base64-encoded 32-byte Fernet key
  - Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
  - Example: `gAAAAABh7kPY8V9_wXCvf3Hn_R0lH0...`

### Optional

- **CREDENTIAL_SERVICE_PORT** - Service port (default: 8002)
- **LOG_LEVEL** - Logging level (default: INFO)
  - Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test

```bash
pytest tests/test_encryption.py -v
```

### Test Coverage

- **Encryption** (3 tests) - encrypt, decrypt, error handling
- **Log Sanitization** (3 tests) - redaction patterns, JSON/text handling
- **API Endpoints** (8+ tests) - CRUD operations, error codes, status codes

## Security Considerations

### Encryption

- Master encryption key (`CREDENTIAL_ENCRYPTION_KEY`) must be kept secure
- Store in restricted `.env` file (chmod 600) or secrets manager
- Rotate key periodically (requires re-encryption of all credentials)
- Use different keys for development vs production

### Credential Storage

- Passwords are encrypted with Fernet (AES-128 CBC + HMAC SHA256)
- Encrypted data is base64-encoded and stored as TEXT in database
- Usernames are stored in plaintext for operational visibility and domain lookup
- Never expose encrypted_data or password in logs (automatic sanitization)

### Access Control

- No authentication in Phase 1 (single-user, trusted network)
- Future: API key authentication for multi-user support
- All credential access logged in system_logs table with timestamp, service_name, correlation_id

### Log Sanitization

Automatic redaction of sensitive fields:
- password, credential, secret, token, key, api_key, auth, encrypted_data

Replace sensitive values with `[REDACTED]` in all logs.

## Deployment

### Docker Compose

Service is typically deployed as part of the trading-report stack:

```yaml
credential-service:
  build: ./services/credential-service
  container_name: trading-credential-service
  environment:
    DATABASE_URL: postgresql://user:password@postgres:5432/trading_reports
    CREDENTIAL_ENCRYPTION_KEY: ${CREDENTIAL_ENCRYPTION_KEY}
    LOG_LEVEL: INFO
  ports:
    - "8002:8002"
  depends_on:
    postgres:
      condition: service_healthy
  networks:
    - trading-network
```

### Kubernetes (Future)

- Use Secrets for CREDENTIAL_ENCRYPTION_KEY and DATABASE_URL
- Mount as environment variables in Pod
- Set resource limits (requests/limits)
- Configure liveness/readiness probes on /health endpoint

## Troubleshooting

### Connection Errors

```
Failed to initialize connection pool: could not connect to server
```

- Verify DATABASE_URL is correct
- Check PostgreSQL is running and accessible
- Verify database exists and user has permissions

### Encryption Key Errors

```
CREDENTIAL_ENCRYPTION_KEY must be 32-byte base64-encoded Fernet key
```

- Generate new key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- Verify key format is base64-encoded
- Key must be exactly 32 bytes after base64 decoding

### Decryption Failures

```
Failed to decrypt credentials for domain broker.com: Invalid token or wrong key
```

- Possible causes: wrong encryption key, corrupted encrypted_data, key rotation
- Check encryption key has not changed since credential was created
- Verify encrypted_data in database is valid base64

### 409 Conflict on Creation

```
Credential already exists for domain broker.com
```

- Domain must be unique
- To update existing credential: use PUT endpoint instead
- To replace: delete (mark inactive) then create new

## Performance

- Encryption/decryption: < 1ms per operation
- Domain lookup with index: < 5ms
- Connection pooling reduces overhead for concurrent requests
- Credential caching at scraper level prevents repeated API calls

## Integration with Scraper Service

Scraper service retrieves credentials via:

```python
# Get credential by domain
import httpx

async def get_credential(domain: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            'http://credential-service:8002/api/v1/credentials/domain/{domain}'
        )
        if response.status_code == 404:
            # Fallback to environment variables
            return {
                'username': os.environ.get('TRADING_PORTAL_USERNAME'),
                'password': os.environ.get('TRADING_PORTAL_PASSWORD'),
            }
        elif response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'Failed to retrieve credentials: {response.text}')
```

## Future Enhancements

- [ ] API key authentication for multi-user support
- [ ] Per-domain rate limiting
- [ ] Credential expiration alerts
- [ ] Automatic key rotation
- [ ] Credential versioning/history
- [ ] Integration with password managers (1Password, LastPass)
- [ ] Web UI for credential management (Phase 2)
- [ ] Scheduled credential rotation with operator notifications

## References

- [Cryptography Library](https://cryptography.io/)
- [Fernet](https://cryptography.io/en/latest/fernet/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/)
