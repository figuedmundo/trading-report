-- Create security_events table for audit logging
-- Stores all webhook security events for compliance and investigation

BEGIN;

-- Create security_events table with JSONB for extensible metadata
CREATE TABLE IF NOT EXISTS security_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    endpoint VARCHAR(255),
    request_headers JSONB,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Create index on ip_address for per-IP queries
CREATE INDEX IF NOT EXISTS idx_security_events_ip ON security_events(ip_address);

-- Create index on event_type for filtering by event type
CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);

-- Create index on created_at for time-range queries (descending for recent-first)
CREATE INDEX IF NOT EXISTS idx_security_events_created ON security_events(created_at DESC);

-- Create composite index for filtered time-range queries
CREATE INDEX IF NOT EXISTS idx_security_events_type_created ON security_events(event_type, created_at DESC);

-- Add table and column comments for documentation
COMMENT ON TABLE security_events IS 'Audit log for all webhook security events including signature failures, rate limits, and IP bans';
COMMENT ON COLUMN security_events.id IS 'Unique identifier for security event';
COMMENT ON COLUMN security_events.event_type IS 'Type of security event: signature_validation_failed, ip_not_whitelisted, rate_limit_exceeded, ip_banned, ip_unbanned, suspicious_pattern, connection_throttled';
COMMENT ON COLUMN security_events.ip_address IS 'Source IP address that triggered the security event';
COMMENT ON COLUMN security_events.endpoint IS 'Request endpoint path (e.g., /webhook/email)';
COMMENT ON COLUMN security_events.request_headers IS 'Filtered request headers (sensitive values removed, only header names logged)';
COMMENT ON COLUMN security_events.metadata IS 'Additional event-specific context (e.g., rate_limit_remaining, ban_duration, provider_detected, user_agent_hash)';
COMMENT ON COLUMN security_events.created_at IS 'Timestamp when security event occurred';

COMMIT;
