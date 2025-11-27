-- Migration: Create notifications_delivery_log table (append-only audit trail)
-- Date: 2025-11-27
-- Purpose: Track all notification delivery attempts with complete audit trail

BEGIN;

-- Create notifications_delivery_log table (append-only)
CREATE TABLE notifications_delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    channel notification_channel NOT NULL,
    recipient TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'sent', 'failed', 'rate_limited'
    sent_at TIMESTAMPTZ,
    latency_ms INTEGER,
    external_id TEXT,  -- email Message-ID or Telegram message_id
    error_code VARCHAR(50),
    error_message TEXT,
    retry_after_seconds INTEGER,  -- For rate limiting
    metadata JSONB DEFAULT '{}',  -- Additional delivery context
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX idx_delivery_log_notification_id ON notifications_delivery_log(notification_id);
CREATE INDEX idx_delivery_log_channel ON notifications_delivery_log(channel);
CREATE INDEX idx_delivery_log_created_at ON notifications_delivery_log(created_at DESC);
CREATE INDEX idx_delivery_log_status ON notifications_delivery_log(status);

-- Constraint: enforce append-only design (no updates after creation)
-- This is enforced at the application level, but database triggers can strengthen it
ALTER TABLE notifications_delivery_log ENABLE ROW LEVEL SECURITY;

-- Grant appropriate permissions
GRANT INSERT ON notifications_delivery_log TO postgres;
GRANT SELECT ON notifications_delivery_log TO postgres;

COMMIT;
