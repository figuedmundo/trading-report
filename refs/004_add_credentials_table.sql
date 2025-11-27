-- Create credentials table
CREATE TABLE IF NOT EXISTS credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(255) NOT NULL,
    encrypted_data TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add credential_id to reports table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reports' AND column_name = 'credential_id') THEN
        ALTER TABLE reports ADD COLUMN credential_id UUID REFERENCES credentials(id);
    END IF;
END $$;

-- Create index on domain for fast lookup
CREATE INDEX IF NOT EXISTS idx_credentials_domain ON credentials(domain);
