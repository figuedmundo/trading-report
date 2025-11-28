-- Create ip_allowlist table for dynamic IP allowlist management
-- Supports runtime IP management without service restart

BEGIN;

-- Create ip_allowlist table with CIDR range support
CREATE TABLE IF NOT EXISTS ip_allowlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ip_address VARCHAR(45) NOT NULL UNIQUE,
    description TEXT,
    enabled BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Create partial index on enabled IPs for fast query performance
CREATE INDEX IF NOT EXISTS idx_ip_allowlist_enabled
ON ip_allowlist(enabled)
WHERE enabled = true;

-- Create trigger function for automatic updated_at timestamp
CREATE OR REPLACE FUNCTION update_ip_allowlist_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at column
DROP TRIGGER IF EXISTS trigger_update_ip_allowlist_updated_at ON ip_allowlist;
CREATE TRIGGER trigger_update_ip_allowlist_updated_at
BEFORE UPDATE ON ip_allowlist
FOR EACH ROW
EXECUTE FUNCTION update_ip_allowlist_updated_at();

-- Add table and column comments for documentation
COMMENT ON TABLE ip_allowlist IS 'Dynamic IP allowlist for webhook endpoint access control with CIDR range support';
COMMENT ON COLUMN ip_allowlist.id IS 'Unique identifier for IP allowlist entry';
COMMENT ON COLUMN ip_allowlist.ip_address IS 'IP address or CIDR range (e.g., 192.168.1.0/24, 149.72.0.0/16)';
COMMENT ON COLUMN ip_allowlist.description IS 'Human-readable description of IP purpose (e.g., "Mailgun server", "Test environment")';
COMMENT ON COLUMN ip_allowlist.enabled IS 'Whether this IP is currently allowed (soft delete flag)';
COMMENT ON COLUMN ip_allowlist.created_at IS 'Timestamp when IP was added to allowlist';
COMMENT ON COLUMN ip_allowlist.updated_at IS 'Timestamp when IP allowlist entry was last modified';

COMMIT;
