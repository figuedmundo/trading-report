-- Create ip_bans table for persistent IP ban storage
-- Maintains ban list across service restarts

BEGIN;

-- Create ip_bans table for automatic IP ban tracking
CREATE TABLE IF NOT EXISTS ip_bans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ip_address VARCHAR(45) NOT NULL,
    banned_until TIMESTAMPTZ NOT NULL,
    reason TEXT,
    attempt_count INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Create index on ip_address for ban lookups
CREATE INDEX IF NOT EXISTS idx_ip_bans_ip ON ip_bans(ip_address);

-- Create index on banned_until for cleanup queries and expiry checks
CREATE INDEX IF NOT EXISTS idx_ip_bans_banned_until ON ip_bans(banned_until);

-- Add table and column comments for documentation
COMMENT ON TABLE ip_bans IS 'Persistent storage of banned IP addresses with automatic expiry support';
COMMENT ON COLUMN ip_bans.id IS 'Unique identifier for ban entry';
COMMENT ON COLUMN ip_bans.ip_address IS 'IP address that has been banned';
COMMENT ON COLUMN ip_bans.banned_until IS 'Timestamp when ban expires (for automatic cleanup)';
COMMENT ON COLUMN ip_bans.reason IS 'Reason for ban (e.g., "Exceeded rate limit threshold", "Failed signature validation 10 times")';
COMMENT ON COLUMN ip_bans.attempt_count IS 'Number of failed attempts that triggered the ban';
COMMENT ON COLUMN ip_bans.created_at IS 'Timestamp when IP was banned';

COMMIT;
