-- Add Credentials Table Migration
-- Creates the credentials table for secure credential storage with encryption support

BEGIN;

-- Create credentials table with enhanced schema
CREATE TABLE IF NOT EXISTS credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Domain and credentials
    domain VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    encrypted_data TEXT NOT NULL,

    -- Portal-specific metadata
    metadata JSONB DEFAULT '{}',

    -- Status and tracking
    is_active BOOLEAN DEFAULT true NOT NULL,
    last_used_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    UNIQUE (domain),
    CONSTRAINT encrypted_data_not_empty CHECK (encrypted_data IS NOT NULL AND encrypted_data <> ''),
    CONSTRAINT valid_domain CHECK (domain ~ '^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$')
);

-- Add composite index for fast active credential lookup
CREATE INDEX IF NOT EXISTS idx_credentials_domain_active ON credentials(domain, is_active);

-- Create trigger function for credentials updated_at
CREATE OR REPLACE FUNCTION update_credentials_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on credentials table
CREATE TRIGGER IF NOT EXISTS update_credentials_updated_at
    BEFORE UPDATE ON credentials
    FOR EACH ROW
    EXECUTE FUNCTION update_credentials_updated_at();

-- Add foreign key from reports.credential_id to credentials.id if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_reports_credential_id'
        AND table_name = 'reports'
    ) THEN
        ALTER TABLE reports
        ADD CONSTRAINT fk_reports_credential_id
        FOREIGN KEY (credential_id) REFERENCES credentials(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Add table and column comments
COMMENT ON TABLE credentials IS 'Securely stores encrypted trading portal credentials with domain lookup';
COMMENT ON COLUMN credentials.id IS 'Unique identifier (UUID)';
COMMENT ON COLUMN credentials.domain IS 'Portal domain for credential lookup (e.g., broker.com)';
COMMENT ON COLUMN credentials.username IS 'Portal username (stored in plaintext for operational visibility)';
COMMENT ON COLUMN credentials.encrypted_data IS 'Encrypted password using Fernet symmetric encryption, base64-encoded';
COMMENT ON COLUMN credentials.metadata IS 'Portal-specific configuration (login URLs, form selectors, 2FA settings)';
COMMENT ON COLUMN credentials.is_active IS 'Boolean flag for credential rotation support (true = active)';
COMMENT ON COLUMN credentials.last_used_at IS 'Timestamp of last credential retrieval for audit trail';
COMMENT ON COLUMN credentials.created_at IS 'Timestamp when credential was created';
COMMENT ON COLUMN credentials.updated_at IS 'Timestamp when credential was last modified, automatically updated by trigger';

COMMIT;
