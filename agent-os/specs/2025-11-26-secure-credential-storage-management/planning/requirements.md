# Spec Requirements: Secure Credential Storage & Management

## Initial Description

Implement encrypted credential vault for trading portal username/password; support per-report credential overrides; ensure credentials never logged or exposed in system output.

This feature is part of Phase 1 MVP - Core Email-to-Report Pipeline, roadmap item #2, size estimate: S (Small).

## Requirements Discussion

### First Round Questions

Since user requested sensible defaults be chosen, the following decisions were made based on best practices and project constraints:

**Q1: Encryption Implementation**
**Decision:** Use Python cryptography library (Fernet symmetric encryption) with master encryption key stored in environment variable (CREDENTIAL_ENCRYPTION_KEY). This provides strong encryption (AES-128 CBC with HMAC) while keeping implementation simple and avoiding external dependencies like HashiCorp Vault in Phase 1.

**Q2: Encryption Layer**
**Decision:** Application-layer encryption within FastAPI service. The service encrypts credentials before writing to database and decrypts when retrieving. This keeps the database layer simpler and consolidates security logic in the application.

**Q3: Default Credentials Fallback**
**Decision:** Support fallback to environment variables (TRADING_PORTAL_USERNAME, TRADING_PORTAL_PASSWORD) when reports.credential_id is NULL. This allows smooth transition from current environment-variable-based approach to database-stored credentials without breaking existing workflows.

**Q4: Credential Logging Security**
**Decision:** Implement automatic sanitization layer that redacts any fields matching patterns like: password, credential, secret, token, key, api_key, auth. This applies to all log statements across all services to prevent accidental credential exposure.

**Q5: Management Interface**
**Decision:** Provide REST API endpoints for CRUD operations on credentials:
- POST /api/v1/credentials - Create new credential
- GET /api/v1/credentials?domain=example.com - Retrieve by domain
- PUT /api/v1/credentials/{id} - Update credential
- DELETE /api/v1/credentials/{id} - Delete credential

No admin UI in Phase 1 (can use curl/Postman for management).

**Q6: Credential Retrieval Method**
**Decision:** Domain-based lookup. When scraper needs credentials, it queries: GET /api/v1/credentials?domain=broker.com. The service returns the most recent active credential for that domain. Domain extracted from report_url using Python's urllib.parse.

**Q7: Credential Rotation Strategy**
**Decision:** Simple replacement model - one active credential per domain at a time. When updating credentials via PUT endpoint, the service:
1. Creates new credential record with new encrypted data
2. Updates reports.credential_id to point to new credential
3. Marks old credential as inactive (or deletes if configured)

No automatic rotation in Phase 1; operator manually updates when portal credentials change.

**Q8: Portal-Specific Metadata**
**Decision:** Include JSONB metadata field in credentials table for portal-specific configurations:
```json
{
  "portal_type": "broker_portal",
  "2fa_enabled": false,
  "security_questions": ["What is your favorite color?"],
  "custom_selectors": {
    "username_field": "#login-email",
    "password_field": "#login-password",
    "submit_button": "button[type=submit]"
  },
  "login_url": "https://portal.example.com/login",
  "requires_captcha": false
}
```

This allows Playwright scraper to adapt to different portal login flows without code changes.

**Q9: Database Reorganization**
**Decision:** YES - Reorganize database structure as part of this spec:

Current problematic structure:
```
postgres/
  migrations/README.md
  sample_data.sql
  init.sql
  maintenance/*.sql
  monitoring/*.sql
```

New organized structure:
```
database/
  migrations/
    001_initial_schema.sql
    002_add_indexes.sql
    003_add_views.sql
    004_add_credentials_table.sql  <- NEW MIGRATION
  schemas/
    database_schema.sql  (complete schema from previous spec)
  scripts/
    init.sql  (initialization script)
    sample_data.sql  (test data)
  maintenance/
    archive_logs.sql
    check_stuck_reports.sql
    slow_queries.sql
  monitoring/
    health_check.sql
    notification_delivery.sql
    disk_usage.sql
    processing_stats.sql
  README.md  (database documentation)
```

Rationale: Aligns with architecture defined in project structure, separates concerns (migrations vs monitoring vs maintenance), and makes it clear this is a database service directory, not PostgreSQL-specific tooling.

**Q10: Decryption Failure Handling**
**Decision:** Fail fast with clear error message, no fallback to environment variables on decryption failure. If decryption fails:
1. Log ERROR with correlation_id and credential_id
2. Return HTTP 500 with message: "Failed to decrypt credentials for domain X"
3. Alert operator via system_logs table
4. Do NOT retry automatically (likely indicates key rotation or corrupted data)

This prevents silent failures and ensures credential issues are immediately visible.

### Existing Code to Reference

**User-Provided Similar Features:**

1. **Existing Migration File:** `refs/004_add_credentials_table.sql`
   - Basic credentials table structure already drafted
   - Includes: id (UUID), domain, encrypted_data, created_at, updated_at
   - Has foreign key relationship to reports table (credential_id)
   - Includes domain index for fast lookup
   - Needs enhancement: metadata field, active status flag, updated encryption approach

2. **Database Schema from Previous Spec:** `agent-os/specs/2025-11-25-postgresql-schema-data-persistence/spec.md`
   - Reports table already has credential_id UUID column with foreign key to credentials(id)
   - System_logs table available for audit logging of credential access
   - UUID pattern established across all tables
   - JSONB metadata pattern established for flexible schemas

3. **Tech Stack Context:**
   - Project uses Python 3.11+ with FastAPI for services
   - PostgreSQL 16.1+ database with SQLAlchemy 2.0.35
   - Environment variables managed via .env file with python-dotenv
   - Docker Compose for service orchestration
   - N8N for workflow management

**Code Patterns to Follow:**

From tech-stack.md:
- Use FastAPI async routes for credential API
- Use Pydantic models for request/response validation
- Use SQLAlchemy for database operations
- Store master encryption key in .env file (CREDENTIAL_ENCRYPTION_KEY)
- Never log credentials (implement automatic sanitization)
- Use structured logging with python-json-logger

From database spec:
- Use UUID primary keys (uuid_generate_v4())
- Use TIMESTAMPTZ for timestamps
- Include created_at, updated_at on all tables
- Use JSONB for flexible metadata
- Add appropriate indexes for query patterns
- Include comments on tables and columns

### Follow-up Questions

No follow-up questions needed. All critical requirements have been addressed through sensible default decisions aligned with project architecture and best practices.

## Visual Assets

No visual assets provided.

## Requirements Summary

### Functional Requirements

**Core Credential Management:**
- Encrypt trading portal username/password pairs before storing in database
- Support multiple credentials per domain (though only one active at a time in Phase 1)
- Store portal-specific metadata (login URLs, form selectors, 2FA settings)
- Provide REST API for CRUD operations on credentials
- Support domain-based credential lookup for scraper service
- Allow per-report credential overrides via reports.credential_id foreign key

**Security Features:**
- Use Fernet symmetric encryption (AES-128 CBC + HMAC) from Python cryptography library
- Store master encryption key in environment variable (CREDENTIAL_ENCRYPTION_KEY)
- Never expose credentials in logs, API responses, or system output
- Implement automatic log sanitization for fields matching: password, credential, secret, token, key
- Fail fast on decryption errors with clear error messages
- Log all credential access attempts in system_logs table for audit trail

**Fallback & Migration:**
- Support fallback to environment variables (TRADING_PORTAL_USERNAME, TRADING_PORTAL_PASSWORD) when credential_id is NULL
- This allows gradual migration from current environment-variable approach
- Eventually deprecate environment variables in favor of database-stored credentials

**API Endpoints:**
- POST /api/v1/credentials - Create new credential (domain, username, password, metadata)
- GET /api/v1/credentials?domain=example.com - Retrieve active credential for domain
- PUT /api/v1/credentials/{id} - Update existing credential (rotates encrypted data)
- DELETE /api/v1/credentials/{id} - Delete credential (marks inactive or hard delete)
- GET /api/v1/credentials/{id} - Get specific credential by ID

**Integration Points:**
- Scraper service calls GET /api/v1/credentials?domain=X before logging into portal
- Email webhook service can optionally specify credential_id when creating report
- System admin uses curl/Postman to manage credentials via API
- N8N workflow can trigger credential rotation on schedule if configured

### Reusability Opportunities

**Database Patterns:**
- Reuse UUID primary key pattern from reports, analyses tables
- Reuse JSONB metadata pattern for portal-specific configs
- Reuse TIMESTAMPTZ created_at/updated_at pattern with automatic triggers
- Reuse foreign key with ON DELETE SET NULL pattern (reports.credential_id)

**API Patterns:**
- Reuse FastAPI structure from existing services (if any exist)
- Reuse Pydantic validation models pattern
- Reuse error response format from existing API endpoints
- Reuse environment variable loading with python-dotenv

**Security Patterns:**
- Establish log sanitization utility that can be reused by all services
- Establish encryption/decryption utility functions for future sensitive data
- Establish environment variable validation pattern for required secrets

**Service Structure:**
- Follow microservice pattern established in project architecture
- Implement as standalone credential-service or integrate into scraper-service
- Use Docker container with health check endpoint
- Connect to same PostgreSQL database as other services

### Scope Boundaries

**In Scope:**
- Encrypted storage of portal credentials in PostgreSQL
- REST API for credential CRUD operations
- Domain-based credential lookup
- Per-report credential override support (via credential_id foreign key)
- Automatic log sanitization to prevent credential exposure
- Fallback to environment variables for backward compatibility
- Database reorganization from postgres/ to database/ directory
- Migration file 004_add_credentials_table.sql enhancement
- Integration with scraper service for credential retrieval
- Audit logging of credential access in system_logs table

**Out of Scope:**
- Admin web UI for credential management (Phase 2+ feature)
- Automatic credential rotation on schedule (manual rotation only in Phase 1)
- Multi-user credential isolation (single-user system in Phase 1)
- OAuth/SSO integration with trading portals (username/password only)
- Credential strength validation or password policy enforcement
- Credential expiration/aging alerts
- HashiCorp Vault or external secrets management integration (Phase 3+)
- Encrypted backups of credentials table (standard database backup used)
- Hardware security module (HSM) integration

**Future Enhancements (Phase 2+):**
- Web UI for credential management
- Scheduled credential rotation with operator notifications
- Credential versioning/history tracking
- Multi-user credential isolation with row-level security
- Integration with password managers (1Password, LastPass APIs)
- Credential health monitoring (detect portal login failures due to bad credentials)

### Technical Considerations

**Encryption Strategy:**
- Library: Python cryptography (Fernet)
- Algorithm: AES-128 CBC with HMAC SHA256 for authentication
- Key Storage: Environment variable CREDENTIAL_ENCRYPTION_KEY (32-byte base64-encoded)
- Key Rotation: Not automated; requires manual key change and re-encryption of all credentials
- Encrypted Format: Store as TEXT in PostgreSQL (base64-encoded Fernet token)

**Database Changes:**
- New migration: 004_add_credentials_table.sql
- Enhance existing migration draft from refs/ directory
- Add columns: metadata (JSONB), is_active (BOOLEAN), last_used_at (TIMESTAMPTZ)
- Maintain foreign key from reports.credential_id to credentials.id ON DELETE SET NULL
- Add index on (domain, is_active) for fast lookup of active credentials per domain
- Add trigger for updated_at timestamp management

**Service Architecture Decision:**
- Option A: Standalone credential-service (separate FastAPI microservice)
  - Pros: Clear separation of concerns, reusable by multiple services
  - Cons: Additional service to deploy and monitor
- Option B: Integrate into scraper-service
  - Pros: Fewer services to manage, scraper is primary credential consumer
  - Cons: Couples credential logic to scraper service
- **Recommended:** Option A (standalone service) for better separation and future extensibility

**API Security:**
- No authentication in Phase 1 (single-user, trusted network)
- API accessible only from Docker network (not exposed publicly)
- Future: Add API key authentication in Phase 2 for multi-user support

**Error Handling:**
- Decryption failure: Return 500 error, log ERROR, do NOT retry
- Missing credential for domain: Return 404 error, log WARNING
- Invalid encryption key: Fail service startup, log CRITICAL
- Database connection failure: Retry with exponential backoff, log ERROR

**Logging & Audit:**
- Log all credential creation/update/deletion in system_logs
- Log credential retrieval attempts (domain, timestamp, correlation_id)
- Sanitize logs automatically to prevent accidental credential exposure
- Include credential_id in scraper logs for traceability (but NOT decrypted values)

**Database Reorganization Details:**
- Move postgres/ directory to database/
- Organize migrations into numbered sequence (001, 002, 003, 004)
- Separate maintenance scripts from monitoring scripts
- Update Makefile commands to reflect new paths
- Update docker-compose.yml volume mounts if needed
- Update service environment variables for database connection
- Update CLAUDE.md with new database structure

**Environment Variables Required:**
```bash
# Master encryption key (32-byte base64-encoded)
CREDENTIAL_ENCRYPTION_KEY=<base64-encoded-32-byte-key>

# Database connection (existing)
DATABASE_URL=postgresql://trading_user:password@postgres:5432/trading_reports

# Fallback credentials (existing, for backward compatibility)
TRADING_PORTAL_USERNAME=<username>
TRADING_PORTAL_PASSWORD=<password>

# Service configuration
CREDENTIAL_SERVICE_PORT=8002
LOG_LEVEL=INFO
```

**Testing Strategy:**
- Unit tests for encryption/decryption functions
- Unit tests for log sanitization utility
- Integration tests for API endpoints (CRUD operations)
- Integration tests for scraper credential retrieval flow
- Test decryption failure handling
- Test fallback to environment variables
- Test log sanitization with various credential patterns

**Performance Considerations:**
- Encryption/decryption is fast (< 1ms per operation)
- Database lookup by domain with index is fast (< 5ms)
- Cache decrypted credentials in memory for scraper session (avoid repeated decryption)
- No performance impact expected for modest volume (10-50 reports/day)

**Migration from Current Approach:**
1. Deploy credential service with API endpoints
2. Create credentials via API for each trading portal
3. Update environment variables to include CREDENTIAL_ENCRYPTION_KEY
4. Test credential retrieval from scraper service
5. Update reports to reference credential_id (via admin script or manual SQL)
6. Verify fallback to environment variables works for NULL credential_id
7. Gradually migrate all reports to use database credentials
8. Eventually remove TRADING_PORTAL_USERNAME/PASSWORD from environment

**Security Best Practices:**
- Rotate CREDENTIAL_ENCRYPTION_KEY periodically (e.g., annually)
- Store .env file with restricted permissions (chmod 600)
- Use different encryption keys for development vs production
- Never commit encryption key or credentials to git
- Document key rotation procedure for operators
- Consider encrypted database backups (pg_dump with encryption) in production
