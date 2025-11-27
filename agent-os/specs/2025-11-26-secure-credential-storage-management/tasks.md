# Task Breakdown: Secure Credential Storage & Management

## Overview
Total Tasks: 42
Estimated Total Effort: 5 days (Medium feature)
Key Dependencies: Database setup -> Encryption -> API -> Integration -> Testing

## Task List

### Phase 1: Infrastructure & Database Setup

#### Task Group 1: Database Directory Reorganization
**Dependencies:** None
**Complexity:** Small
**Estimated Effort:** 2-3 hours

- [x] 1.0 Complete database directory reorganization
  - [x] 1.1 Create new database/ directory structure
    - Create: `database/migrations/`, `database/schemas/`, `database/scripts/`, `database/maintenance/`, `database/monitoring/`
    - Create: `database/README.md` with migration documentation and new structure explanation
    - Keep all existing SQL files organized without modifications at this stage
  - [x] 1.2 Move and rename existing migration files to numbered sequence
    - Create migration sequence from existing postgres/ files
    - Goal: Establish 001, 002, 003 pattern for existing migrations
    - Ensure all existing migrations are now in `database/migrations/` with consistent naming
  - [x] 1.3 Move scripts and maintenance files
    - Move `postgres/init.sql` to `database/scripts/init.sql`
    - Move `postgres/sample_data.sql` to `database/scripts/sample_data.sql`
    - Move any maintenance scripts to `database/maintenance/`
    - Move any monitoring scripts to `database/monitoring/`
  - [x] 1.4 Update docker-compose.yml references
    - Update volume mount from `./postgres:/docker-entrypoint-initdb.d` to `./database/scripts:/docker-entrypoint-initdb.d`
    - Verify other postgres service configurations remain unchanged
  - [x] 1.5 Update Makefile database commands
    - Update any database-related make targets to reference `database/` path instead of `postgres/`
    - Ensure all database commands (db-shell, db-backup, db-restore, etc.) work with new paths
  - [x] 1.6 Update CLAUDE.md documentation
    - Update directory structure section to reflect new `database/` layout
    - Document migration file naming convention (001_*, 002_*, etc.)
    - Add reference to `database/README.md` for detailed database documentation
  - [x] 1.7 Verify all references in codebase updated
    - Search for any hardcoded postgres/ paths in configuration files
    - Verify GitHub Actions workflows or CI/CD scripts reference correct paths

**Acceptance Criteria:**
- Database directory moved from `postgres/` to `database/`
- All files reorganized into appropriate subdirectories (migrations, scripts, maintenance, monitoring)
- `database/README.md` created with documentation
- docker-compose.yml volume mounts updated
- Makefile database targets work with new paths
- No breaking changes to existing services

---

#### Task Group 2: Enhanced Credentials Table Migration
**Dependencies:** Task Group 1
**Complexity:** Small
**Estimated Effort:** 1-2 hours

- [x] 2.0 Complete enhanced credentials table migration
  - [x] 2.1 Create migration 004_add_credentials_table.sql with enhancements
    - Create file at: `database/migrations/004_add_credentials_table.sql`
    - Base on: `refs/004_add_credentials_table.sql`
    - Add columns to spec requirements:
      - `username VARCHAR(255) NOT NULL`
      - `metadata JSONB DEFAULT '{}'` (for portal-specific configs like login URLs, form selectors)
      - `is_active BOOLEAN DEFAULT true` (support credential rotation)
      - `last_used_at TIMESTAMPTZ` (audit trail for credential usage)
    - Maintain existing columns: `id`, `domain`, `encrypted_data`, `created_at`, `updated_at`
  - [x] 2.2 Add database constraints and indexes
    - Add UNIQUE constraint on `(domain)` for one active credential per domain
    - Add COMPOSITE index on `(domain, is_active)` for fast active credential lookup
    - Add CHECK constraint: `encrypted_data IS NOT NULL AND encrypted_data <> ''`
    - Add table comment describing purpose and field semantics
    - Add column comments for `encrypted_data`, `metadata`, `is_active`, `last_used_at`
  - [x] 2.3 Implement updated_at trigger
    - Create trigger function: `update_credentials_updated_at()` if not exists
    - Apply trigger to credentials table for automatic `updated_at` timestamp on UPDATE
    - Follow pattern from PostgreSQL schema spec for consistency
  - [x] 2.4 Add foreign key relationship
    - Add FOREIGN KEY from `reports.credential_id` to `credentials.id` ON DELETE SET NULL
    - Verify this is idempotent (skip if FK already exists from previous migration)
  - [x] 2.5 Write 2-3 focused tests for migration
    - Test migration runs successfully without errors
    - Test credentials table created with all required columns
    - Test indexes and constraints are in place
    - Verify trigger function exists and works on UPDATE
  - [x] 2.6 Verify migration tests pass
    - Run ONLY the 2-3 migration tests written in 2.5
    - Execute migration in clean test database
    - Verify table structure matches requirements

**Acceptance Criteria:**
- Migration file created at correct path with all required enhancements
- Credentials table has all required columns and constraints
- Indexes on (domain) and (domain, is_active) exist
- CHECK constraint on encrypted_data present
- Trigger for updated_at working correctly
- Foreign key relationship with reports.credential_id configured
- Migration tests pass (2-3 focused tests)

---

### Phase 2: Core Encryption & Utility Functions

#### Task Group 3: Encryption/Decryption Utilities
**Dependencies:** None (can start in parallel with Phase 1)
**Complexity:** Medium
**Estimated Effort:** 4-5 hours

- [x] 3.0 Complete encryption/decryption utilities
  - [x] 3.1 Write 2-3 focused tests for encryption utilities
    - Test encryption produces valid Fernet tokens
    - Test decryption recovers original plaintext
    - Test decryption fails gracefully with corrupted data
    - Test invalid encryption key format causes startup failure
    - Skip: edge cases like very long passwords, special characters (unless business-critical)
  - [x] 3.2 Create encryption module structure
    - Create file: `services/credential-service/src/encryption.py` (or appropriate location)
    - Module purpose: centralized encryption/decryption logic for credentials
    - Import from cryptography library (Fernet)
  - [x] 3.3 Implement encryption key validation
    - Validate `CREDENTIAL_ENCRYPTION_KEY` environment variable at service startup
    - Must be 32-byte base64-encoded string (Fernet requirement)
    - Fail immediately with CRITICAL log and exit code 1 if missing or invalid format
    - Error message: "CREDENTIAL_ENCRYPTION_KEY must be 32-byte base64-encoded Fernet key"
    - Load key during module initialization (before any encryption operations)
  - [x] 3.4 Implement encrypt() function
    - Signature: `encrypt(plaintext: str) -> str` returns base64-encoded Fernet token
    - Load cipher from CREDENTIAL_ENCRYPTION_KEY
    - Convert plaintext to bytes, encrypt, return as base64 TEXT string
    - Handle exceptions: InvalidKey, InvalidToken (should not happen on encrypt, but defensive)
    - Return encrypted token suitable for storage in TEXT column
  - [x] 3.5 Implement decrypt() function
    - Signature: `decrypt(encrypted_data: str) -> str` returns plaintext
    - Load cipher from CREDENTIAL_ENCRYPTION_KEY
    - Convert base64 string to bytes, decrypt, return plaintext
    - On InvalidToken or InvalidKey: raise exception with correlation_id context
    - Exception will be caught by API layer and converted to 500 response
  - [x] 3.6 Document encryption module
    - Add module docstring explaining encryption approach (Fernet AES-128 CBC + HMAC)
    - Document key format requirements
    - Document exception scenarios and how they're handled
    - Add function docstrings with type hints
  - [x] 3.7 Ensure encryption tests pass
    - Run ONLY the 2-3 encryption tests written in 3.1
    - Verify encryption produces valid output format
    - Verify decryption recovers original values
    - Test fails appropriately on corrupted data

**Acceptance Criteria:**
- Encryption module created with encrypt() and decrypt() functions
- CREDENTIAL_ENCRYPTION_KEY validation at startup (fail fast)
- Encryption uses Fernet (AES-128 CBC + HMAC) from cryptography library
- Encryption returns base64-encoded tokens suitable for TEXT column storage
- Decryption raises clear exceptions on failure
- All 2-3 encryption utility tests pass

---

#### Task Group 4: Log Sanitization Utility
**Dependencies:** None (can start in parallel)
**Complexity:** Small
**Estimated Effort:** 2-3 hours

- [x] 4.0 Complete log sanitization utility
  - [x] 4.1 Write 2-3 focused tests for log sanitization
    - Test password field redaction in plain text logs
    - Test credential field redaction in JSON logs
    - Test multiple sensitive fields redacted in single message
    - Skip: exhaustive pattern matching for all possible variations
  - [x] 4.2 Create log sanitization module
    - Create file: `services/credential-service/src/logging.py` or shared utils location
    - Module purpose: redact sensitive fields from log messages before output
    - Patterns to redact: password, credential, secret, token, key, api_key, auth, encrypted_data
  - [x] 4.3 Implement sanitize_log_message() function
    - Signature: `sanitize_log_message(message: str) -> str`
    - Redact values of fields matching sensitive patterns (case-insensitive)
    - Replace sensitive values with "[REDACTED]" in output
    - Preserve field names for debugging context
    - Handle both JSON and plain text log formats
    - Example: `"password=secret123"` becomes `"password=[REDACTED]"`
  - [x] 4.4 Implement structured log wrapper
    - For structured logging (JSON format), wrap sensitive fields
    - Handle both dict and string log records
    - Ensure all services can use this sanitizer
  - [x] 4.5 Document sanitization patterns
    - Document which field names trigger sanitization
    - Explain why sanitization is critical for security
    - Provide usage examples for other services
  - [ ] 4.6 Ensure sanitization tests pass
    - Run ONLY the 2-3 sanitization tests written in 4.1
    - Verify sensitive fields redacted in plain text
    - Verify sensitive fields redacted in JSON
    - Verify non-sensitive fields preserved

**Acceptance Criteria:**
- Log sanitization utility created and working
- Sensitive field patterns redacted from logs
- "[REDACTED]" placeholder used consistently
- Both JSON and plain text log formats supported
- All 2-3 sanitization tests pass
- Ready to be integrated into all services

---

### Phase 3: Credential Service API & Database Integration

#### Task Group 5: Credential Service Database Layer
**Dependencies:** Task Groups 2 & 3
**Complexity:** Medium
**Estimated Effort:** 4-5 hours

- [x] 5.0 Complete credential service database layer
  - [x] 5.1 Write 2-3 focused tests for database operations
    - Test create credential writes encrypted data to database
    - Test retrieve credential by domain returns active credential
    - Test update credential marks old as inactive, creates new record
    - Skip: comprehensive coverage of all error scenarios
  - [x] 5.2 Create database connection module
    - Create file: `services/credential-service/src/database.py`
    - Reuse pattern from: `services/email-webhook/src/database.py` (ThreadedConnectionPool)
    - Implement: init_connection_pool(), close_connection_pool(), get_db_connection(), return_db_connection()
    - Use minconn=2, maxconn=10 for connection pooling
    - Read configuration from environment variables via python-dotenv
  - [x] 5.3 Create SQLAlchemy models
    - Create file: `services/credential-service/src/models.py`
    - Define Credential model with columns: id, domain, username, encrypted_data, metadata, is_active, last_used_at, created_at, updated_at
    - Use SQLAlchemy declarative base following project conventions
    - Add table comments and column comments for documentation
  - [x] 5.4 Implement credential repository functions
    - create_credential(domain, username, password, metadata): Insert new credential with encrypted password
    - get_credential_by_domain(domain): Select active credential by domain
    - get_credential_by_id(credential_id): Select credential by UUID
    - update_credential(credential_id, username, password, metadata): Update existing credential
    - delete_credential(credential_id): Mark credential as inactive (logical delete)
    - list_all_credentials(): Return all credentials with encrypted_data excluded
  - [x] 5.5 Implement credential query helpers
    - get_active_credential_for_domain(domain): Query with WHERE domain=X AND is_active=true
    - Use composite index on (domain, is_active) for performance
    - Update last_used_at timestamp on retrieval
    - Return structured response with metadata and username (NOT encrypted_data)
  - [x] 5.6 Ensure database layer tests pass
    - Run ONLY the 2-3 tests written in 5.1
    - Verify credentials stored and retrieved correctly
    - Test encryption/decryption flow end-to-end with database
    - Do NOT run entire application test suite

**Acceptance Criteria:**
- Database connection pooling implemented
- SQLAlchemy models defined with all required columns
- CRUD functions implemented and working
- Domain-based lookup queries optimized with indexes
- All 2-3 database layer tests pass
- Encrypted data properly handled in all operations

---

#### Task Group 6: Credential Service Pydantic Models
**Dependencies:** Task Group 3
**Complexity:** Small
**Estimated Effort:** 2-3 hours

- [x] 6.0 Complete Pydantic request/response models
  - [x] 6.1 Create models module
    - Create file: `services/credential-service/src/schemas.py`
    - Define Pydantic models for API request/response validation
    - Follow pattern from: `services/email-webhook/src/models.py`
  - [x] 6.2 Implement CredentialRequest model
    - Fields: domain (str, required), username (str, required), password (str, required), metadata (dict, optional)
    - Add Field validators for domain format (valid URL domain)
    - Add Field validators for password length (min 8 characters)
    - Use populate_by_name=True for flexible field naming
  - [x] 6.3 Implement CredentialResponse model
    - Fields: id (UUID), domain (str), username (str), metadata (dict), is_active (bool), last_used_at (optional datetime)
    - DO NOT include encrypted_data in response
    - Include created_at, updated_at timestamps
    - Include correlation_id for tracing
  - [x] 6.4 Implement CredentialListResponse model
    - Fields: credentials (list[CredentialResponse]), total (int), correlation_id
    - Used for GET /api/v1/credentials responses
  - [x] 6.5 Implement ErrorResponse model
    - Fields: code (str), message (str), details (optional dict), correlation_id
    - Include status_code for HTTP response mapping
  - [ ] 6.6 Implement HealthResponse model
    - Fields: status (str), database_connected (bool), timestamp (datetime), correlation_id
    - Used for GET /health endpoint

**Acceptance Criteria:**
- All Pydantic models defined with proper validation
- encrypted_data NEVER appears in response models
- Models follow project patterns and conventions
- All models include correlation_id for tracing
- Validation rules enforced at model level

---

#### Task Group 7: Credential Service REST API Endpoints
**Dependencies:** Task Groups 5, 6
**Complexity:** Large
**Estimated Effort:** 6-7 hours

- [x] 7.0 Complete credential service API endpoints
  - [x] 7.1 Write 2-4 focused tests for API endpoints
    - Test POST /api/v1/credentials creates credential and returns 201
    - Test GET /api/v1/credentials?domain=X returns credential and 200
    - Test GET /api/v1/credentials/{id} returns credential by ID
    - Test 404 returned for non-existent domain/credential
    - Test 500 returned on decryption failure (corrupted encrypted_data)
    - Skip: exhaustive testing of all edge cases and error scenarios
  - [x] 7.2 Create FastAPI service main.py
    - Create file: `services/credential-service/src/main.py`
    - Initialize FastAPI app with title, version, description
    - Reuse pattern from: `services/email-webhook/src/main.py`
    - Implement @app.on_event("startup") to initialize database connection pool
    - Implement @app.on_event("shutdown") to close database pool
    - Configure structured logging with service name "credential-service"
  - [x] 7.3 Implement POST /api/v1/credentials endpoint
    - Accept CredentialRequest body (domain, username, password, metadata)
    - Validate domain is unique (return 409 Conflict if exists)
    - Encrypt password using encryption utility
    - Store credential in database
    - Return CredentialResponse with 201 status
    - Include correlation_id in response
    - Log INFO: "Credential created for domain X" with metadata (domain, username, correlation_id)
  - [x] 7.4 Implement GET /api/v1/credentials?domain=X endpoint
    - Accept domain as query parameter
    - Extract domain using urllib.parse.urlparse if full URL provided
    - Query active credential for domain
    - Return 404 if not found
    - On success: decrypt encrypted_data and return CredentialResponse with plaintext
    - Update last_used_at timestamp when retrieved
    - Log DEBUG: "Credential retrieved for domain X" (credential_id, requesting_service, correlation_id)
    - Return 200 with CredentialResponse
  - [x] 7.5 Implement GET /api/v1/credentials/{id} endpoint
    - Accept UUID credential_id as path parameter
    - Query credential by ID
    - Return 404 if not found
    - Decrypt and return CredentialResponse with plaintext
    - Update last_used_at timestamp
    - Log DEBUG credential retrieval
  - [x] 7.6 Implement PUT /api/v1/credentials/{id} endpoint
    - Accept credential_id and CredentialRequest body
    - Validate credential exists
    - Update existing credential record
    - Encrypt new password and update encrypted_data
    - Update metadata if provided
    - Return updated CredentialResponse with 200
    - Log INFO: "Credential updated for domain X" with metadata (old_username, new_username, correlation_id)
  - [x] 7.7 Implement DELETE /api/v1/credentials/{id} endpoint
    - Accept credential_id as path parameter
    - Validate credential exists
    - Mark as inactive (logical delete) - do NOT hard delete
    - Return 204 No Content or CredentialResponse with 200
    - Log WARNING: "Credential deleted for domain X" with metadata (credential_id, correlation_id)
  - [ ] 7.8 Implement GET /health endpoint
    - Return HealthResponse with service status
    - Include database connectivity check (attempt query to credentials table)
    - Return 200 if healthy, 503 if database unavailable
    - Include timestamp and correlation_id
  - [ ] 7.9 Implement error handling and status codes
    - 201 Created: successful POST /api/v1/credentials
    - 200 OK: successful GET/PUT operations
    - 204 No Content: successful DELETE
    - 404 Not Found: missing credential or domain
    - 409 Conflict: duplicate domain on creation
    - 500 Internal Server Error: decryption failures, unhandled exceptions
    - 503 Service Unavailable: database connection failures
    - Include ErrorResponse with code, message, details, correlation_id
  - [ ] 7.10 Implement correlation_id tracking
    - Generate UUID correlation_id on every request (from header if provided, else generate)
    - Pass correlation_id through all logging statements
    - Include in all response bodies for distributed tracing
    - Add to audit log entries in system_logs table
  - [ ] 7.11 Implement request/response logging
    - Log every request with: method, endpoint, correlation_id, timestamp
    - Log every response with: status_code, correlation_id, response_time
    - Use structured logging (JSON format) for easy parsing
    - Ensure credentials redacted in all logs (use sanitization utility from Task Group 4)
  - [ ] 7.12 Ensure API tests pass
    - Run ONLY the 2-4 tests written in 7.1
    - Verify all CRUD operations work
    - Test error scenarios (404, 409, 500)
    - Verify credentials NOT exposed in responses

**Acceptance Criteria:**
- All REST API endpoints implemented (POST, GET, PUT, DELETE, health)
- All endpoints validate input and return appropriate status codes
- Credentials properly encrypted/decrypted in all operations
- All 2-4 API tests pass
- Correlation IDs tracked throughout
- All logs sanitized (credentials never exposed)
- Health check validates database connectivity

---

### Phase 4: Service Integration & Fallback Mechanism

#### Task Group 8: Scraper Service Integration
**Dependencies:** Task Groups 3, 5, 7
**Complexity:** Medium
**Estimated Effort:** 4-5 hours

- [ ] 8.0 Complete scraper service credential integration
  - [ ] 8.1 Write 2-3 focused tests for scraper credential flow
    - Test scraper retrieves credential by domain from API
    - Test scraper handles 404 (credential not found) and falls back to environment variables
    - Test scraper handles 500 (decryption failure) and marks report as failed
    - Skip: comprehensive edge case testing
  - [ ] 8.2 Create credential client module for scraper
    - Create file: `services/playwright-scraper/src/credential_client.py` (or integrate into existing service)
    - Purpose: HTTP client for credential service API
    - Implement: get_credential(domain, correlation_id) async function
    - Use aiohttp or requests library (async preferred)
  - [ ] 8.3 Implement domain extraction from report_url
    - Function: extract_domain(report_url) -> str
    - Use urllib.parse.urlparse(report_url).netloc
    - Handle edge cases: port numbers in domain, internationalized domains
    - Extract ONLY the hostname, not port or path
  - [ ] 8.4 Implement credential retrieval with fallback logic
    - When processing report:
      1. If report.credential_id exists: query GET /api/v1/credentials/{credential_id}
      2. Else: extract domain from report_url and query GET /api/v1/credentials?domain=X
      3. If 404: fallback to environment variables (TRADING_PORTAL_USERNAME, TRADING_PORTAL_PASSWORD)
      4. If 500: log ERROR, mark report as failed, do NOT fallback
    - Log WARNING when fallback to environment variables is used (encourage migration)
    - Include correlation_id in all API calls and logs
  - [ ] 8.5 Implement credential caching per session
    - Cache decrypted credentials in memory to avoid repeated API calls
    - Cache key: domain or credential_id
    - Invalidate cache on credential update (via webhook or background task in Phase 2)
    - Use TTL (time-to-live) on cache: 1 hour expiration for security
  - [ ] 8.6 Update report creation flow
    - When creating report (POST to reports table): optionally include credential_id
    - If using database credential: set credential_id foreign key
    - If using environment variable fallback: set credential_id to NULL
    - Update scraper logic to pass credential_id to reports table
  - [ ] 8.7 Implement error handling for credential failures
    - On 404 (credential not found):
      - Log WARNING: "Credential not found for domain X, falling back to environment variables"
      - Use TRADING_PORTAL_USERNAME and TRADING_PORTAL_PASSWORD from environment
    - On 500 (decryption failure):
      - Log ERROR: "Failed to decrypt credentials for domain X"
      - Mark report status as FAILED
      - Store error_message: "Credential decryption failed - possible key rotation issue"
      - Do NOT retry (fail fast)
  - [ ] 8.8 Update scraper service configuration
    - Add CREDENTIAL_SERVICE_URL environment variable (e.g., http://credential-service:8002)
    - Add CREDENTIAL_SERVICE_TIMEOUT (default 5 seconds)
    - Add to .env.example with documentation
  - [ ] 8.9 Ensure scraper integration tests pass
    - Run ONLY the 2-3 tests written in 8.1
    - Test credential retrieval succeeds
    - Test fallback to environment variables works
    - Test decryption failure handling

**Acceptance Criteria:**
- Scraper can retrieve credentials from credential service API
- Fallback to environment variables works when credential_id NULL
- Decryption failures handled gracefully (mark report as failed)
- Credential caching implemented for performance
- Reports can specify credential_id for per-report override
- All 2-3 scraper integration tests pass

---

#### Task Group 9: Audit Logging & System Logs Integration
**Dependencies:** Task Groups 4, 7
**Complexity:** Medium
**Estimated Effort:** 3-4 hours

- [ ] 9.0 Complete audit logging for credential operations
  - [ ] 9.1 Create audit logging utility
    - Create file: `services/credential-service/src/audit.py`
    - Purpose: centralized audit logging to system_logs table
    - Implement: log_credential_event(service_name, log_level, message, metadata, correlation_id)
  - [ ] 9.2 Log credential creation
    - Event: "Credential created for domain {domain}"
    - Level: INFO
    - Metadata: {domain, username (never password), correlation_id}
    - Insert to system_logs with service_name="credential-service"
  - [ ] 9.3 Log credential retrieval
    - Event: "Credential retrieved for domain {domain}"
    - Level: DEBUG
    - Metadata: {domain, credential_id, requesting_service, correlation_id}
    - Update credentials.last_used_at timestamp
  - [ ] 9.4 Log credential update
    - Event: "Credential updated for domain {domain}"
    - Level: INFO
    - Metadata: {credential_id, old_username, new_username, correlation_id}
    - Never include password in metadata
  - [ ] 9.5 Log credential deletion
    - Event: "Credential deleted for domain {domain}"
    - Level: WARNING
    - Metadata: {credential_id, domain, correlation_id}
  - [ ] 9.6 Log decryption failures
    - Event: "Failed to decrypt credentials for domain {domain}"
    - Level: ERROR
    - Metadata: {credential_id, error_type, correlation_id}
    - Alert operator to possible key rotation or data corruption
  - [ ] 9.7 Implement service-wide log sanitization
    - All logging statements use sanitization utility from Task Group 4
    - Ensure credentials NEVER appear in logs
    - Use credential_id for traceability instead of sensitive data
  - [ ] 9.8 Add logging context propagation
    - Ensure correlation_id passed through all function calls
    - Use Python logging context (logging.LogRecord) to attach correlation_id
    - Make correlation_id available in all log statements

**Acceptance Criteria:**
- Audit logging utility created and integrated
- All credential operations logged to system_logs table
- Logs include appropriate metadata for debugging
- Credentials NEVER exposed in any logs
- correlation_id tracked throughout all operations
- Log levels appropriate (INFO/DEBUG/WARNING/ERROR)

---

### Phase 5: Configuration & Environment Setup

#### Task Group 10: Environment Variables & Configuration
**Dependencies:** Task Groups 3, 7, 8
**Complexity:** Small
**Estimated Effort:** 1-2 hours

- [x] 10.0 Complete environment configuration setup
  - [x] 10.1 Update .env.example file
    - Add: CREDENTIAL_ENCRYPTION_KEY=<base64-encoded-32-byte-key> with comment
    - Add: CREDENTIAL_SERVICE_PORT=8002 with comment
    - Add: CREDENTIAL_SERVICE_URL=http://credential-service:8002 (for scraper integration)
    - Add: CREDENTIAL_SERVICE_TIMEOUT=5 (seconds)
    - Keep existing: TRADING_PORTAL_USERNAME, TRADING_PORTAL_PASSWORD (for fallback)
    - Update comments explaining when each is used
  - [x] 10.2 Document environment variable requirements
    - Create section in CLAUDE.md: "Environment Variables Reference"
    - Explain CREDENTIAL_ENCRYPTION_KEY: "32-byte base64-encoded Fernet key for credential encryption"
    - Explain CREDENTIAL_SERVICE_URL: "Internal Docker network URL for credential API"
    - Explain CREDENTIAL_SERVICE_TIMEOUT: "API timeout in seconds"
    - Document migration path: "Start with environment variables, migrate to database credentials"
  - [x] 10.3 Create helper utility for encryption key generation
    - Create file: `scripts/generate_encryption_key.py`
    - Purpose: generate random 32-byte base64-encoded Fernet key
    - Usage: `python scripts/generate_encryption_key.py`
    - Output: print key suitable for copy-paste to .env
    - Add documentation: how operators should generate and rotate keys

**Acceptance Criteria:**
- .env.example updated with all required variables
- CLAUDE.md updated with variable documentation
- Encryption key generation script provided
- All configuration documented for operators

---

#### Task Group 11: Docker Service Configuration
**Dependencies:** Task Groups 7, 10
**Complexity:** Small
**Estimated Effort:** 2-3 hours

- [x] 11.0 Complete docker-compose configuration
  - [x] 11.1 Create credential-service definition in docker-compose.yml
    - Service name: credential-service
    - Container name: credential-service
    - Image: (build from Dockerfile or use custom image)
    - Port: map internal 8002 to host or internal network only
    - Volumes: (if needed for development hot-reload)
    - Environment variables: CREDENTIAL_ENCRYPTION_KEY, DATABASE_URL, LOG_LEVEL
    - Depends on: postgres service
    - Health check: GET /health endpoint
  - [x] 11.2 Add credential-service Dockerfile
    - Create file: `services/credential-service/Dockerfile`
    - Base image: python:3.11-slim
    - Install dependencies: pip install -r requirements.txt
    - Copy source code to /app
    - Set working directory: /app
    - Expose port 8002
    - Run command: gunicorn or uvicorn main:app --host 0.0.0.0 --port 8002
  - [x] 11.3 Create requirements.txt for credential-service
    - File: `services/credential-service/requirements.txt`
    - Dependencies: fastapi, uvicorn, psycopg2-binary, pydantic, python-cryptography, python-dotenv, etc.
    - Pin versions for reproducibility
  - [ ] 11.4 Update Makefile with credential-service targets
    - Add: `make test-credential-service` - run credential service tests
    - Add: `make shell-credential-service` - open shell in running credential service container
    - Add: `make logs-credential-service` - view credential service logs
  - [ ] 11.5 Verify service networking
    - Credential service accessible from scraper service via http://credential-service:8002
    - Both services connected to same Docker network
    - Test with curl or internal API calls

**Acceptance Criteria:**
- docker-compose.yml includes credential-service definition
- Dockerfile created and builds successfully
- requirements.txt includes all dependencies
- Makefile targets work for credential service
- Service is properly networked for scraper integration

---

### Phase 6: Testing & Validation

#### Task Group 12: Integration Testing
**Dependencies:** Task Groups 5-11
**Complexity:** Medium
**Estimated Effort:** 4-5 hours

- [ ] 12.0 Complete integration testing across components
  - [ ] 12.1 Review existing focused tests from Task Groups 3-7
    - Compile all tests written during development:
      - 2-3 encryption utility tests (Task Group 3)
      - 2-3 log sanitization tests (Task Group 4)
      - 2-3 database layer tests (Task Group 5)
      - 2-3 API endpoint tests (Task Group 7)
      - 2-3 scraper integration tests (Task Group 8)
    - Total existing tests: approximately 10-15 focused tests
  - [ ] 12.2 Identify critical integration gaps
    - Create credential via API, verify encryption in database, retrieve and decrypt correctly
    - Scraper retrieves credential by domain, authenticates to portal successfully
    - Fallback to environment variables when credential_id NULL
    - Audit logging records credential access with sanitized metadata
    - Decryption failure marked as 500 error, report status updated to FAILED
    - Domain uniqueness enforced (no duplicate credentials per domain)
    - Credential update creates new record, marks old as inactive
  - [ ] 12.3 Write up to 8 additional strategic integration tests
    - Maximum 8 new tests to fill identified gaps
    - Focus on critical workflows: create -> retrieve -> use in scraper -> audit log
    - Test error scenarios: 404 (missing credential), 409 (duplicate domain), 500 (decryption failure)
    - Test fallback mechanism: credential_id NULL -> environment variables
    - Skip: comprehensive edge case testing
  - [ ] 12.4 Test end-to-end credential workflow
    - Create credential via POST /api/v1/credentials
    - Verify encrypted in database
    - Retrieve via GET /api/v1/credentials?domain=X
    - Verify decryption returns plaintext
    - Verify audit log entry created with sanitized metadata
    - Verify last_used_at updated on retrieval
  - [ ] 12.5 Test fallback mechanism
    - Create report with credential_id NULL
    - Scraper queries credential service, gets 404
    - Scraper falls back to TRADING_PORTAL_USERNAME/PASSWORD from environment
    - Verify WARNING log: "falling back to environment variables"
    - Verify successful authentication with fallback credentials
  - [ ] 12.6 Test decryption failure handling
    - Corrupt encrypted_data in database (truncate or modify)
    - Scraper retrieves credential via API
    - API returns 500: "Failed to decrypt credentials"
    - Scraper marks report as FAILED
    - Verify ERROR log with correlation_id and credential_id
    - Verify no fallback to environment variables (fail fast)
  - [ ] 12.7 Run feature-specific tests only
    - Run ONLY tests related to this feature specification
    - Total expected tests: approximately 18-23 tests (10-15 existing + up to 8 new)
    - Do NOT run entire application test suite
    - Verify all critical workflows pass
  - [ ] 12.8 Verify test coverage for critical paths
    - Encryption/decryption: covered in Task Group 3
    - Log sanitization: covered in Task Group 4
    - Database CRUD: covered in Task Group 5
    - API endpoints: covered in Task Group 7
    - Scraper integration: covered in Task Group 8
    - Error scenarios: covered in Task Group 12 (integration phase)

**Acceptance Criteria:**
- All 18-23 feature-specific tests pass
- Critical user workflows tested: create credential -> scraper retrieves -> authenticate
- Error scenarios tested: missing credential, decryption failure, duplicate domain
- Fallback mechanism tested and working
- No more than 8 additional tests added in this phase (gap filling only)
- All logs verified to be sanitized (credentials never exposed)

---

#### Task Group 13: Security Validation & Manual Testing
**Dependencies:** Task Groups 9, 12
**Complexity:** Medium
**Estimated Effort:** 3-4 hours

- [ ] 13.0 Complete security validation
  - [ ] 13.1 Verify encryption key validation
    - Test with invalid key format (not base64, wrong length)
    - Verify service fails at startup with CRITICAL log
    - Verify error message clear: "CREDENTIAL_ENCRYPTION_KEY must be 32-byte base64-encoded"
  - [ ] 13.2 Verify credentials never exposed in logs
    - Run all services with LOG_LEVEL=DEBUG
    - Process credential creation, retrieval, update operations
    - Search log output for any plaintext passwords or encrypted values
    - Verify only credential_id and domain appear in logs (no sensitive data)
    - Test with password containing special characters: @#$%^&*()
  - [ ] 13.3 Verify credentials never exposed in API responses
    - Call POST /api/v1/credentials with password
    - Verify response includes username and metadata but NOT password
    - Verify response includes NOT encrypted_data (even as base64)
    - Call GET /api/v1/credentials?domain=X
    - Verify decrypted password returned (necessary for scraper) but marked as sensitive in response type
  - [ ] 13.4 Verify database encryption at rest
    - Dump credentials table from PostgreSQL
    - Verify encrypted_data column contains base64 text (not plaintext password)
    - Verify decryption requires correct CREDENTIAL_ENCRYPTION_KEY
    - Test with wrong encryption key: verify decryption fails
  - [ ] 13.5 Verify audit trail completeness
    - Create, retrieve, update, delete credential
    - Query system_logs table
    - Verify each operation logged with: timestamp, service_name, log_level, message, metadata, correlation_id
    - Verify metadata includes domain and username but never password
  - [ ] 13.6 Manual testing with curl/Postman
    - Test POST /api/v1/credentials
    - Test GET /api/v1/credentials?domain=example.com
    - Test GET /api/v1/credentials/{id}
    - Test PUT /api/v1/credentials/{id}
    - Test DELETE /api/v1/credentials/{id}
    - Test GET /health
    - Document test cases and results
  - [ ] 13.7 Verify fallback behavior
    - Create report with credential_id NULL
    - Verify scraper uses TRADING_PORTAL_USERNAME/PASSWORD from environment
    - Verify logs show WARNING about fallback usage
  - [ ] 13.8 Load testing (basic)
    - Test credential retrieval under 10 concurrent requests
    - Verify no race conditions in credential creation (duplicate domain check)
    - Verify cache prevents repeated database queries for same credential

**Acceptance Criteria:**
- Encryption key validation enforced at startup
- Credentials NEVER exposed in logs or API responses
- Encrypted data verified in database
- Audit trail complete with all operations logged
- Manual testing with curl/Postman successful
- Fallback mechanism verified working
- Basic load testing passes

---

#### Task Group 14: Documentation & Operator Guidance
**Dependencies:** Task Groups 10, 13
**Complexity:** Small
**Estimated Effort:** 2-3 hours

- [x] 14.0 Complete documentation
  - [x] 14.1 Create credential-service README
    - File: `services/credential-service/README.md`
    - Purpose: API documentation, setup, usage examples
    - Include: service architecture, endpoints, request/response examples
    - Document error responses and HTTP status codes
    - Include: curl examples for all endpoints
  - [x] 14.2 Document encryption key generation and rotation
    - File: `database/README.md` section on "Credential Security"
    - Document: how to generate encryption key using `scripts/generate_encryption_key.py`
    - Document: key rotation procedure (requires re-encrypting all credentials)
    - Document: storing encryption key safely (restricted file permissions, .env)
    - Document: difference between development and production keys
  - [x] 14.3 Update CLAUDE.md with credential service details
    - Add section: "Credential Service Architecture"
    - Document: encryption approach (Fernet AES-128 CBC + HMAC)
    - Document: API endpoints and usage
    - Document: integration with scraper service
    - Document: fallback to environment variables for backward compatibility
    - Add example curl commands for credential management
  - [x] 14.4 Document migration path from environment variables to database
    - File: `database/README.md` or new `MIGRATION_GUIDE.md`
    - Step 1: Generate CREDENTIAL_ENCRYPTION_KEY and add to .env
    - Step 2: Deploy credential service
    - Step 3: Create credentials for each portal via POST /api/v1/credentials
    - Step 4: Test scraper retrieval with database credentials
    - Step 5: Update existing reports to reference credential_id (optional admin script)
    - Step 6: Verify fallback to environment variables still works
    - Eventually: remove TRADING_PORTAL_USERNAME/PASSWORD from environment
  - [x] 14.5 Create Postman collection or curl examples
    - Document: POST /api/v1/credentials (create)
    - Document: GET /api/v1/credentials?domain=X (retrieve by domain)
    - Document: PUT /api/v1/credentials/{id} (update)
    - Document: DELETE /api/v1/credentials/{id} (delete)
    - Include: example request/response payloads
  - [ ] 14.6 Document troubleshooting guide
    - Include: common errors (CREDENTIAL_ENCRYPTION_KEY not set, database connection failed)
    - Include: debugging steps (check logs, verify credentials in database)
    - Include: recovery procedures (key rotation, corrupted data)
  - [ ] 14.7 Update main README.md
    - Add reference to credential service in architecture section
    - Document when to use database credentials vs environment variables
    - Document security best practices

**Acceptance Criteria:**
- credential-service README created with API documentation
- Encryption key generation and rotation procedures documented
- CLAUDE.md updated with credential service details
- Migration guide provided for operators
- Postman/curl examples documented
- Troubleshooting guide created
- Main README.md updated

---

### Phase 7: Final Verification & Cleanup

#### Task Group 15: Code Review & Standards Compliance
**Dependencies:** All previous task groups
**Complexity:** Medium
**Estimated Effort:** 3-4 hours

- [ ] 15.0 Complete code review and standards compliance
  - [ ] 15.1 Verify coding style consistency
    - All files follow naming conventions from `agent-os/standards/global/coding-style.md`
    - Meaningful variable/function names (no abbreviations)
    - Consistent indentation (spaces, no tabs)
    - No dead code or commented-out blocks
    - DRY principle followed (no duplicate code)
  - [ ] 15.2 Verify database standards compliance
    - All migrations follow `agent-os/standards/backend/migrations.md`
    - Credentials table has UUID primary key, TIMESTAMPTZ timestamps
    - Comments on table and columns documenting purpose
    - Indexes on frequently-queried columns (domain, is_active)
    - Foreign keys with appropriate ON DELETE behavior
  - [ ] 15.3 Verify model standards compliance
    - Pydantic models follow `agent-os/standards/backend/models.md`
    - Clear field naming, appropriate data types
    - Validation at both model and database levels
    - Comments explaining complex fields or constraints
  - [ ] 15.4 Verify API standards compliance
    - API endpoints follow `agent-os/standards/backend/api.md`
    - RESTful design (POST create, GET retrieve, PUT update, DELETE delete)
    - Consistent response format with status codes
    - Error responses include clear messages
    - Correlation IDs for distributed tracing
  - [ ] 15.5 Verify test standards compliance
    - Tests follow `agent-os/standards/testing/test-writing.md`
    - Tests focus on critical user workflows (not exhaustive edge cases)
    - Minimal tests during development (approximately 18-23 total)
    - Tests are fast and independent
    - Clear test names describing what's tested
  - [ ] 15.6 Verify error handling standards compliance
    - Follow `agent-os/standards/global/error-handling.md`
    - Specific exceptions caught (not bare Exception)
    - Error messages clear and actionable
    - Errors logged with context (correlation_id, service_name)
    - Appropriate HTTP status codes returned
  - [ ] 15.7 Verify validation standards compliance
    - Follow `agent-os/standards/global/validation.md`
    - Validation at system boundaries (API endpoints)
    - Pydantic models validate request data
    - Database constraints enforce data integrity
    - Clear error messages on validation failure
  - [ ] 15.8 Verify commenting standards
    - Follow `agent-os/standards/global/commenting.md`
    - Comments explain "why" not "what"
    - Docstrings on modules, classes, functions
    - Complex logic explained with comments
    - No obvious or redundant comments

**Acceptance Criteria:**
- All code follows project coding standards
- Database migrations follow migration best practices
- API design follows REST standards
- Tests are focused on critical workflows
- Error handling is clear and consistent
- Validation occurs at system boundaries
- Comments explain intent and complex logic

---

#### Task Group 16: Pre-Release Verification
**Dependencies:** Task Groups 12-15
**Complexity:** Small
**Estimated Effort:** 2 hours

- [ ] 16.0 Complete pre-release verification
  - [ ] 16.1 Run all feature-specific tests one final time
    - Run all 18-23 tests together
    - Verify all pass without errors
    - Verify no flaky tests
  - [ ] 16.2 Verify all database migrations run successfully
    - Run migration 004_add_credentials_table.sql
    - Verify table created with all columns and constraints
    - Verify indexes and triggers in place
    - Verify foreign key relationship with reports table
  - [ ] 16.3 Verify environment configuration complete
    - .env.example includes all required variables
    - CLAUDE.md documents all environment variables
    - Operator has guide to generate CREDENTIAL_ENCRYPTION_KEY
    - docker-compose.yml includes credential-service
  - [ ] 16.4 Verify no hardcoded credentials or secrets
    - Search codebase for hardcoded passwords, API keys, encryption keys
    - Verify all sensitive data loaded from environment variables
    - Verify .env file not committed to git (check .gitignore)
  - [ ] 16.5 Verify backward compatibility
    - Existing services (scraper, analyzer, etc.) still work
    - Fallback to environment variables works for reports with credential_id NULL
    - Database schema changes don't break existing queries
    - Existing migration files still run successfully
  - [ ] 16.6 Perform smoke test
    - Start all services: `make dev`
    - Verify credential-service starts without errors
    - Verify health check returns 200: `curl http://localhost:8002/health`
    - Create test credential via API
    - Retrieve credential via API and verify decryption works
    - Verify audit log entry created in system_logs
    - Verify logs contain no plaintext credentials

**Acceptance Criteria:**
- All 18-23 tests pass
- Database migration runs successfully
- Environment configuration complete
- No hardcoded secrets in code
- Backward compatibility maintained
- Smoke test successful

---

## Execution Summary

### Recommended Implementation Sequence

1. **Phase 1: Infrastructure** (2-3 days)
   - Task Group 1: Database directory reorganization
   - Task Group 2: Enhanced credentials table migration
   - Start in parallel: Task Groups 3, 4 (encryption, sanitization)

2. **Phase 2: Core Utilities** (1 day)
   - Task Group 3: Encryption/decryption utilities
   - Task Group 4: Log sanitization utility

3. **Phase 3: Credential Service** (2-3 days)
   - Task Group 5: Database layer (queries, models)
   - Task Group 6: Pydantic schemas
   - Task Group 7: REST API endpoints
   - Task Group 10: Environment configuration (in parallel)
   - Task Group 11: Docker setup (in parallel)

4. **Phase 4: Integration** (1-2 days)
   - Task Group 8: Scraper service integration
   - Task Group 9: Audit logging

5. **Phase 5: Testing** (1-2 days)
   - Task Group 12: Integration testing
   - Task Group 13: Security validation

6. **Phase 6: Documentation & Finalization** (1 day)
   - Task Group 14: Documentation
   - Task Group 15: Code review & standards
   - Task Group 16: Pre-release verification

### Critical Path Dependencies

```
Database Reorganization (1.0)
    ↓
Enhanced Migration (2.0)
    ↓
Database Layer (5.0) ← Encryption (3.0)
    ↓
API Endpoints (7.0)
    ↓
Scraper Integration (8.0)
    ↓
Integration Testing (12.0)
    ↓
Pre-Release (16.0)
```

### Parallel Work Streams

- **Encryption & Sanitization** (Task Groups 3, 4): No dependencies, can start immediately
- **Configuration & Deployment** (Task Groups 10, 11): Depends on API endpoints but can start after
- **Documentation & Testing** (Task Groups 12-15): Wait for core implementation

## Key Success Criteria

1. Credentials encrypted before storage, never logged or exposed
2. API endpoints functional with proper status codes and error handling
3. Scraper service can retrieve and use credentials with fallback to environment variables
4. All operations audited in system_logs with sanitized metadata
5. 18-23 focused tests covering critical workflows
6. All code follows project standards and best practices
7. Documentation complete for operator usage and maintenance
8. Backward compatibility maintained with existing services
