# Specification: Secure Credential Storage & Management

## Goal

Establish a secure, encrypted credential vault for storing trading portal login credentials, enabling the scraper service to authenticate to password-protected portals while ensuring credentials are never exposed in logs or system output, supporting per-report credential overrides, and providing a fallback mechanism for backward compatibility with environment variables.

## User Stories

- As a system operator, I want to securely store multiple trading portal credentials in the database so I can manage credentials for different brokers without modifying environment variables
- As a scraper service, I want to retrieve decrypted credentials on-demand for specific domains so I can authenticate to trading portals without hardcoding passwords
- As a security-conscious user, I want all credential operations to be automatically sanitized from logs so sensitive data is never exposed in system output or debugging traces

## Specific Requirements

**Encrypted Credential Storage**
- Use Python cryptography library (Fernet) for symmetric encryption with AES-128 CBC and HMAC SHA256 authentication
- Store master encryption key in environment variable `CREDENTIAL_ENCRYPTION_KEY` (32-byte base64-encoded)
- Encrypt password before storing in database `encrypted_data` column (TEXT format, base64-encoded Fernet token)
- Store username in plaintext for operational visibility and domain-based lookup
- Include domain field (VARCHAR 255) as primary lookup key for credentials
- Use UNIQUE constraint on domain to enforce one active credential per domain
- Add is_active BOOLEAN flag to support credential rotation without deletion
- Include JSONB metadata column for portal-specific configurations (login URLs, form selectors, 2FA settings)

**REST API for Credential Management**
- Implement FastAPI service with endpoints: POST /api/v1/credentials (create), GET /api/v1/credentials?domain=X (retrieve by domain), GET /api/v1/credentials/{id} (retrieve by ID), PUT /api/v1/credentials/{id} (update), DELETE /api/v1/credentials/{id} (delete/deactivate)
- Use Pydantic models for request/response validation with encrypted_data automatically decrypted on retrieval
- Return 404 for missing credentials, 500 for decryption failures, 201 for successful creation
- Include correlation_id in all responses for distributed tracing
- Implement health check endpoint at GET /health returning service status and database connectivity
- Use domain-based lookup via query parameter: GET /api/v1/credentials?domain=broker.com extracts domain from report_url using urllib.parse
- Support credential override per report via reports.credential_id foreign key (NULL uses fallback to environment variables)

**Automatic Log Sanitization**
- Implement log sanitization utility function that redacts fields matching patterns: password, credential, secret, token, key, api_key, auth, encrypted_data
- Apply sanitization to all log statements across all services (decorator or wrapper function)
- Replace sensitive values with "[REDACTED]" in log output while preserving field names
- Sanitize both structured logging (JSON) and plain text log messages
- Include credential_id in logs for traceability but never include decrypted values
- Log all credential access attempts in system_logs table with metadata (domain, timestamp, service_name, correlation_id)

**Environment Variable Fallback**
- Support fallback to TRADING_PORTAL_USERNAME and TRADING_PORTAL_PASSWORD when reports.credential_id is NULL
- Check environment variables only when database credential lookup returns 404
- Log fallback usage with WARNING level to encourage migration to database-stored credentials
- Document migration path from environment variables to database credentials for operators
- Eventually deprecate environment variable fallback in Phase 2

**Database Reorganization**
- Move postgres/ directory to database/ for clearer semantic meaning
- Organize into subdirectories: migrations/, schemas/, scripts/, maintenance/, monitoring/
- Create numbered migration sequence: 001_initial_schema.sql, 002_add_indexes.sql, 003_add_views.sql, 004_add_credentials_table.sql
- Update docker-compose.yml volume mounts from ./postgres:/docker-entrypoint-initdb.d to ./database/scripts:/docker-entrypoint-initdb.d
- Update Makefile database commands to reference new database/ path
- Move existing files: postgres/init.sql to database/scripts/init.sql, postgres/sample_data.sql to database/scripts/sample_data.sql
- Document new structure in database/README.md with migration instructions

**Enhanced Migration File**
- Extend existing refs/004_add_credentials_table.sql with additional columns: username VARCHAR(255) NOT NULL, metadata JSONB DEFAULT '{}', is_active BOOLEAN DEFAULT true, last_used_at TIMESTAMPTZ
- Add composite index on (domain, is_active) for fast active credential lookup
- Add trigger for updated_at timestamp management (update_credentials_updated_at)
- Add foreign key from reports.credential_id to credentials.id ON DELETE SET NULL
- Include table and column comments for documentation
- Validate encrypted_data is not empty (CHECK constraint)

**Encryption/Decryption Flow**
- On credential creation: validate input, generate Fernet cipher from CREDENTIAL_ENCRYPTION_KEY, encrypt password to token, store token as TEXT in encrypted_data column
- On credential retrieval: read encrypted_data from database, load Fernet cipher with CREDENTIAL_ENCRYPTION_KEY, decrypt token to password, return plaintext password only to scraper service
- On decryption failure: log ERROR with credential_id and correlation_id, return HTTP 500 with message "Failed to decrypt credentials for domain X", do NOT retry or fallback to environment variables
- Validate CREDENTIAL_ENCRYPTION_KEY exists at service startup, fail immediately if missing with CRITICAL log
- Cache decrypted credentials in memory per scraper session (avoid repeated decryption), invalidate cache on credential update

**Integration with Scraper Service**
- Scraper service extracts domain from report_url using urllib.parse.urlparse(report_url).netloc
- Scraper calls GET /api/v1/credentials?domain={domain} to retrieve credentials
- If 404 returned, scraper falls back to environment variables (TRADING_PORTAL_USERNAME, TRADING_PORTAL_PASSWORD)
- If 500 returned (decryption failure), scraper marks report as failed with error_message and logs ERROR
- Scraper passes credential_id to reports table when creating report (optional, for per-report credential tracking)
- Update reports.last_used_at timestamp when credentials are retrieved for audit trail

**Error Handling Requirements**
- Invalid encryption key format: fail service startup with clear error message "CREDENTIAL_ENCRYPTION_KEY must be 32-byte base64-encoded Fernet key"
- Missing encryption key: fail service startup with CRITICAL log and exit code 1
- Decryption failure: return HTTP 500, log ERROR with correlation_id, store error in system_logs table
- Database connection failure: retry with exponential backoff (3 attempts), return HTTP 503 on final failure
- Duplicate domain on creation: return HTTP 409 Conflict with message "Credential already exists for domain X"
- Missing credential on retrieval: return HTTP 404 Not Found with message "No active credential found for domain X"

**Audit Logging Requirements**
- Log credential creation: service_name=credential_service, log_level=INFO, message="Credential created for domain X", metadata includes domain, username, correlation_id
- Log credential retrieval: service_name=credential_service, log_level=DEBUG, message="Credential retrieved for domain X", metadata includes credential_id, requesting_service, correlation_id
- Log credential update: service_name=credential_service, log_level=INFO, message="Credential updated for domain X", metadata includes credential_id, old_username, new_username, correlation_id
- Log credential deletion: service_name=credential_service, log_level=WARNING, message="Credential deleted for domain X", metadata includes credential_id, correlation_id
- Log decryption failure: service_name=credential_service, log_level=ERROR, message="Failed to decrypt credentials", metadata includes credential_id, error_type, correlation_id

## Visual Design

No visual mockups provided for backend API specification.

## Existing Code to Leverage

**refs/004_add_credentials_table.sql - Existing Migration Draft**
- Basic credentials table structure already defined with id (UUID), domain (VARCHAR 255), encrypted_data (TEXT), created_at, updated_at
- Includes foreign key relationship to reports table via credential_id column
- Has domain index for fast lookup (idx_credentials_domain)
- Needs enhancement: add username, metadata, is_active, last_used_at columns; add composite index on (domain, is_active); add trigger for updated_at
- Migration file already uses IF NOT EXISTS pattern for idempotency
- Can be directly moved to database/migrations/004_add_credentials_table.sql with enhancements

**services/email-webhook/src/database.py - Database Connection Pattern**
- Implements psycopg2 ThreadedConnectionPool with minconn=2, maxconn=10 for efficient connection reuse
- Provides init_connection_pool(), close_connection_pool(), get_db_connection(), return_db_connection() functions for lifecycle management
- Uses global _connection_pool instance with safe initialization and cleanup
- Reads database configuration from get_config() utility (environment variables via python-dotenv)
- Can replicate this pattern for credential service database connectivity

**services/email-webhook/src/models.py - Pydantic Request/Response Models**
- Uses Pydantic BaseModel for request validation with Field() for aliases and constraints
- Implements ConfigDict(populate_by_name=True) for flexible field naming
- Defines standardized response models (SuccessResponse, ErrorResponse, HealthResponse) with status patterns
- Includes timestamp and correlation_id fields in all responses for tracing
- Can extend this pattern for CredentialRequest, CredentialResponse, CredentialListResponse models

**services/email-webhook/src/main.py - FastAPI Service Structure**
- FastAPI app initialization with title, version, description metadata
- Implements startup/shutdown event handlers for database pool lifecycle
- Health check endpoint pattern with database connectivity verification
- Uses logging.basicConfig for structured logging with timestamp, service name, log level
- Can replicate this service structure for credential management API

**PostgreSQL Schema from Previous Spec - Database Patterns**
- UUID primary keys via gen_random_uuid() for all tables
- TIMESTAMPTZ for all timestamp fields with automatic NOW() defaults
- JSONB for flexible metadata storage with JSON operator support
- Trigger pattern for automatic updated_at timestamp management (update_updated_at_column function)
- Foreign key with ON DELETE SET NULL for optional relationships (reports.credential_id)
- Can follow these patterns for credentials table design

## Out of Scope

- Admin web UI for credential management (Phase 2+ feature, use curl/Postman for Phase 1)
- Automatic credential rotation on schedule (manual rotation only via PUT endpoint)
- Multi-user credential isolation with row-level security (single-user system in Phase 1)
- OAuth/SSO integration with trading portals (username/password authentication only)
- Credential strength validation or password policy enforcement
- Credential expiration or aging alerts
- HashiCorp Vault or external secrets management integration (Phase 3+)
- Encrypted database backups (standard PostgreSQL backup used)
- Hardware security module (HSM) integration
- Master encryption key rotation procedure (manual operator task, not automated)
- Credential versioning or history tracking (one active credential per domain)
