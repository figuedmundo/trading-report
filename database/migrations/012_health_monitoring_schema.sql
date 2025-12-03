-- Create health monitoring and error logging tables
-- Stores health check results, error logs, and alert delivery tracking
-- All tables use append-only design (except alert_state) for audit compliance

BEGIN;

-- Create health_checks table for storing periodic service health check results
CREATE TABLE IF NOT EXISTS health_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    check_timestamp TIMESTAMPTZ NOT NULL,
    check_duration_ms INT NOT NULL,
    details_json JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes on health_checks for efficient queries
CREATE INDEX IF NOT EXISTS idx_health_checks_service_timestamp
    ON health_checks(service_name, check_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_health_checks_created
    ON health_checks(created_at DESC);

-- Create error_logs table for storing all system errors with full context
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    error_timestamp TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    context_json JSONB DEFAULT '{}'::jsonb NOT NULL,
    source_report_id UUID,
    stack_trace TEXT,
    correlation_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes on error_logs for efficient filtering and retrieval
CREATE INDEX IF NOT EXISTS idx_error_logs_severity_timestamp
    ON error_logs(severity, error_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_error_logs_service_timestamp
    ON error_logs(service_name, error_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_error_logs_correlation_id
    ON error_logs(correlation_id);

CREATE INDEX IF NOT EXISTS idx_error_logs_created
    ON error_logs(created_at DESC);

-- Create alert_logs table for tracking alert generation and delivery
CREATE TABLE IF NOT EXISTS alert_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    error_id UUID NOT NULL,
    alert_timestamp TIMESTAMPTZ NOT NULL,
    alert_type VARCHAR(100) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    delivery_status VARCHAR(20) NOT NULL,
    sent_at TIMESTAMPTZ,
    delivery_latency_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT fk_alert_logs_error_id
        FOREIGN KEY (error_id)
        REFERENCES error_logs(id)
        ON DELETE CASCADE
);

-- Indexes on alert_logs for efficient querying
CREATE INDEX IF NOT EXISTS idx_alert_logs_error_id
    ON alert_logs(error_id);

CREATE INDEX IF NOT EXISTS idx_alert_logs_timestamp
    ON alert_logs(alert_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_alert_logs_delivery_status
    ON alert_logs(delivery_status);

CREATE INDEX IF NOT EXISTS idx_alert_logs_created
    ON alert_logs(created_at DESC);

-- Add table comments for documentation
COMMENT ON TABLE health_checks
    IS 'Stores periodic health check results for all microservices. Append-only design for audit trail.';

COMMENT ON COLUMN health_checks.id
    IS 'Unique identifier for health check record';

COMMENT ON COLUMN health_checks.service_name
    IS 'Name of the service being health checked (email-webhook, playwright-scraper, ai-analyzer, notification-service, n8n)';

COMMENT ON COLUMN health_checks.status
    IS 'Health status: up (healthy), down (unavailable), degraded (partially functional)';

COMMENT ON COLUMN health_checks.check_timestamp
    IS 'Timestamp when health check was performed';

COMMENT ON COLUMN health_checks.check_duration_ms
    IS 'Time taken to complete health check in milliseconds';

COMMENT ON COLUMN health_checks.details_json
    IS 'Additional health check details as JSON (response times, database connectivity status, etc.)';

COMMENT ON TABLE error_logs
    IS 'Append-only log of all errors across the system. Enables audit trail and error analysis.';

COMMENT ON COLUMN error_logs.id
    IS 'Unique identifier for error record';

COMMENT ON COLUMN error_logs.error_timestamp
    IS 'Timestamp when error occurred';

COMMENT ON COLUMN error_logs.service_name
    IS 'Service that encountered the error';

COMMENT ON COLUMN error_logs.error_type
    IS 'Type of error (login_failure, api_timeout, database_error, extraction_failure, etc.)';

COMMENT ON COLUMN error_logs.severity
    IS 'Error severity level: CRITICAL (system-blocking), ERROR (single-report failures), WARNING (non-blocking)';

COMMENT ON COLUMN error_logs.message
    IS 'Human-readable error message';

COMMENT ON COLUMN error_logs.context_json
    IS 'Error context as JSONB (response codes, retry count, external API errors, etc.)';

COMMENT ON COLUMN error_logs.source_report_id
    IS 'Report ID affected by this error (if applicable)';

COMMENT ON COLUMN error_logs.stack_trace
    IS 'Full stack trace for debugging (optional)';

COMMENT ON COLUMN error_logs.correlation_id
    IS 'Correlation ID for tracing related errors across service boundaries';

COMMENT ON TABLE alert_logs
    IS 'Tracks alert generation and email delivery for critical errors';

COMMENT ON COLUMN alert_logs.id
    IS 'Unique identifier for alert record';

COMMENT ON COLUMN alert_logs.error_id
    IS 'Reference to the error that triggered the alert';

COMMENT ON COLUMN alert_logs.alert_timestamp
    IS 'Timestamp when alert was generated';

COMMENT ON COLUMN alert_logs.alert_type
    IS 'Type of alert (critical_error, batch_summary, etc.)';

COMMENT ON COLUMN alert_logs.recipient
    IS 'Email address where alert was sent';

COMMENT ON COLUMN alert_logs.delivery_status
    IS 'Status of alert delivery: pending, sent, failed';

COMMENT ON COLUMN alert_logs.sent_at
    IS 'Timestamp when alert email was successfully sent';

COMMENT ON COLUMN alert_logs.delivery_latency_ms
    IS 'Time in milliseconds from alert generation to delivery';

COMMIT;
