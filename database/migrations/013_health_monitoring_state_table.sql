-- Create alert_state table for alert batching and spam prevention
-- This is the only table in health monitoring that allows UPDATE operations
-- Tracks consecutive failures and suppression windows per service + error_type combination

BEGIN;

CREATE TABLE IF NOT EXISTS alert_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(100) NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    last_alert_sent_at TIMESTAMPTZ,
    consecutive_failure_count INT NOT NULL DEFAULT 0,
    last_error_timestamp TIMESTAMPTZ,
    alert_suppressed_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT uk_alert_state_service_error_type
        UNIQUE (service_name, error_type)
);

-- Indexes on alert_state for efficient queries
CREATE INDEX IF NOT EXISTS idx_alert_state_suppressed_until
    ON alert_state(alert_suppressed_until);

CREATE INDEX IF NOT EXISTS idx_alert_state_updated_at
    ON alert_state(updated_at DESC);

-- Add table comments for documentation
COMMENT ON TABLE alert_state
    IS 'Tracks batching state and suppression windows for alert generation. Only table with UPDATE operations (spam prevention).';

COMMENT ON COLUMN alert_state.id
    IS 'Unique identifier for alert state record';

COMMENT ON COLUMN alert_state.service_name
    IS 'Service name for alert tracking';

COMMENT ON COLUMN alert_state.error_type
    IS 'Error type for alert batching';

COMMENT ON COLUMN alert_state.last_alert_sent_at
    IS 'Timestamp of last alert sent for this service + error_type combination';

COMMENT ON COLUMN alert_state.consecutive_failure_count
    IS 'Number of consecutive failures of same type since last alert';

COMMENT ON COLUMN alert_state.last_error_timestamp
    IS 'Timestamp of most recent error of this type';

COMMENT ON COLUMN alert_state.alert_suppressed_until
    IS 'If set, alerts are suppressed until this timestamp (for auto-recovery)';

COMMIT;
