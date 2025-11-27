# Database Directory

This directory contains all database-related files for the Trading Report Automation system.

## Directory Structure

```
database/
├── migrations/           # Database schema migrations
│   ├── 001_initial_schema.sql
│   ├── 002_add_indexes.sql
│   ├── 003_add_triggers.sql
│   └── 004_add_credentials_table.sql
├── schemas/             # Complete database schema definitions
│   └── database_schema.sql
├── scripts/             # Database initialization and setup scripts
│   ├── init.sql
│   ├── sample_data.sql
│   └── init_database.py
├── maintenance/         # Maintenance scripts for database upkeep
│   └── *.sql
├── monitoring/          # Monitoring and health check queries
│   └── *.sql
└── README.md           # This file
```

## Migrations

Database migrations are numbered sequentially and applied in order:

1. **001_initial_schema.sql** - Creates base tables: reports, report_images, analyses, notifications, system_logs
2. **002_add_indexes.sql** - Adds indexes for common query patterns (performance optimization)
3. **003_add_triggers.sql** - Adds trigger functions for automatic timestamp management
4. **004_add_credentials_table.sql** - Adds credentials table for secure, encrypted credential storage

### Migration Naming Convention

- Format: `NNN_description.sql` where NNN is a 3-digit sequence number
- Migrations are applied in ascending order
- Each migration should be idempotent (using `IF NOT EXISTS` where possible)
- Keep migrations focused on a single logical change

### Running Migrations

Migrations are automatically applied when Docker Compose starts the PostgreSQL service. The initialization order is:

1. `init_database.py` - Python script that sets up roles and initial configuration
2. `database_schema.sql` - Complete schema reference (generated from migrations)
3. Individual migration files (if run independently)

## Schemas

The `schemas/` directory contains reference documentation and complete schema definitions:

- **database_schema.sql** - Complete, unified database schema generated from all migrations (reference only)

## Scripts

The `scripts/` directory contains initialization and setup scripts:

- **init.sql** - Database initialization SQL (roles, extensions, etc.)
- **sample_data.sql** - Sample data for testing and development
- **init_database.py** - Python script for advanced initialization (run by Docker entrypoint)

## Maintenance

Maintenance scripts for regular database upkeep:

- Archiving old logs
- Checking for stuck reports
- Slow query analysis
- Defragmentation and cleanup

## Monitoring

Monitoring scripts for health checks and operational metrics:

- Health check queries
- Notification delivery statistics
- Disk usage monitoring
- Processing statistics and performance metrics

## Credential Storage

The `credentials` table (created in migration 004) stores encrypted trading portal credentials:

### Schema

```sql
credentials (
    id UUID PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) NOT NULL,
    encrypted_data TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
```

### Key Features

- **Encryption**: Passwords encrypted with Fernet (AES-128 CBC + HMAC) before storage
- **Domain Lookup**: Indexed on (domain, is_active) for fast credential retrieval
- **Metadata**: JSONB field for portal-specific configuration (login URLs, form selectors, 2FA settings)
- **Audit Trail**: last_used_at timestamp tracks credential access; system_logs table records all credential operations
- **Status Management**: is_active flag supports credential rotation without deletion

### Encryption Key Management

The master encryption key must be configured via environment variable:

```bash
CREDENTIAL_ENCRYPTION_KEY=<base64-encoded-32-byte-Fernet-key>
```

See `scripts/generate_encryption_key.py` for key generation.

## Database Connection Configuration

PostgreSQL connection details are configured via environment variables:

```bash
DATABASE_URL=postgresql://user:password@host:port/database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=trading_reports
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

## Docker Integration

Volume mount for Docker Compose:

```yaml
volumes:
  - ./database/scripts:/docker-entrypoint-initdb.d
```

This automatically runs all SQL files and Python scripts in `scripts/` during container initialization, in alphabetical order.

## Backup and Recovery

### Full Database Backup

```bash
pg_dump postgresql://user:password@host:port/database > backup.sql
```

### Restore from Backup

```bash
psql postgresql://user:password@host:port/database < backup.sql
```

### Connection Pool Configuration

The application uses psycopg2 ThreadedConnectionPool for efficient connection management:

- minconn: 2 (minimum connections in pool)
- maxconn: 10 (maximum connections in pool)
- Connection timeout: Configurable per service

## Performance Considerations

- Indexes are created on frequently-queried columns (domain, status, created_at, etc.)
- JSONB metadata columns use GIN indexes for efficient key lookups
- Timestamp columns are indexed with DESC for chronological queries
- Partial indexes on status fields to focus on active records

## Compliance and Audit

- **Audit Trail**: system_logs table tracks all important operations with correlation_id for tracing
- **Timestamps**: All tables have created_at and updated_at (automatically managed by triggers)
- **Constraints**: CHECK constraints ensure data integrity
- **Comments**: All tables and columns documented for operational clarity

## Troubleshooting

### Connection Issues

```bash
# Test PostgreSQL connection
psql postgresql://user:password@host:port/database -c "SELECT 1"
```

### Migration Issues

If a migration fails:

1. Check PostgreSQL logs: `docker logs trading-postgres`
2. Verify environment variables are set
3. Ensure database exists and user has permissions
4. Run migrations manually to debug: `psql -f migration_file.sql`

### Performance Issues

1. Check query execution plans: `EXPLAIN ANALYZE <query>`
2. Verify indexes exist: `\d+ <table_name>`
3. Analyze table statistics: `ANALYZE <table_name>`
4. Monitor slow queries in logs

## Security Best Practices

1. **Encryption Key**: Store CREDENTIAL_ENCRYPTION_KEY in secure location (.env with restricted permissions)
2. **Database Backups**: Consider encrypted backups for production (pg_dump with encryption)
3. **Access Control**: Database user should have minimal required permissions
4. **Log Sanitization**: All logs are automatically sanitized to remove credentials
5. **Key Rotation**: Document and test key rotation procedure (requires re-encryption of all credentials)

## Future Enhancements

- [ ] Encrypted database backups (Phase 2)
- [ ] Read replicas for high availability (Phase 2)
- [ ] Connection pooling optimization (Phase 2)
- [ ] Historical audit log archiving (Phase 3)
- [ ] Automated key rotation (Phase 3+)
