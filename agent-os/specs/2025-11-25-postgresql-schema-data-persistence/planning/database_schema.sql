-- Trading Report Automation Database Schema
-- PostgreSQL 16.1+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For better text search

-- Create custom types
CREATE TYPE report_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE notification_channel AS ENUM ('telegram', 'email');
CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'failed', 'retrying');
CREATE TYPE ai_provider AS ENUM ('anthropic', 'groq');
CREATE TYPE sentiment AS ENUM ('bullish', 'bearish', 'neutral', 'mixed');

-- ============================================================================
-- REPORTS TABLE
-- ============================================================================
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Email metadata
    email_received_at TIMESTAMPTZ NOT NULL,
    email_subject TEXT,
    email_from TEXT,
    email_message_id TEXT UNIQUE,
    
    -- Report information
    report_url TEXT NOT NULL,
    report_title TEXT,
    raw_content TEXT,
    
    -- Processing status
    status report_status DEFAULT 'pending' NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    processed_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_url CHECK (report_url ~* '^https?://'),
    CONSTRAINT valid_retry CHECK (retry_count >= 0)
);

-- ============================================================================
-- REPORT IMAGES TABLE
-- ============================================================================
CREATE TABLE report_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    
    -- Image data
    image_url TEXT,
    image_data BYTEA,
    image_hash TEXT, -- SHA256 hash for deduplication
    image_type VARCHAR(50) DEFAULT 'screenshot',
    mime_type VARCHAR(100),
    
    -- Image metadata
    width INTEGER,
    height INTEGER,
    size_bytes INTEGER,
    sequence_order INTEGER DEFAULT 0,
    
    -- Additional info
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Constraints
    CONSTRAINT image_source_check CHECK (
        (image_url IS NOT NULL) OR (image_data IS NOT NULL)
    ),
    CONSTRAINT valid_dimensions CHECK (
        (width IS NULL AND height IS NULL) OR (width > 0 AND height > 0)
    )
);

-- ============================================================================
-- ANALYSES TABLE
-- ============================================================================
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    
    -- AI provider info
    ai_provider ai_provider NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    prompt_template TEXT,
    
    -- Analysis results
    summary TEXT NOT NULL,
    key_trades JSONB DEFAULT '[]'::jsonb,
    market_analysis TEXT,
    recommendations TEXT,
    
    -- Sentiment analysis
    sentiment sentiment,
    confidence_score DECIMAL(3,2),
    
    -- Trading metrics extracted
    win_rate DECIMAL(5,2),
    profit_loss DECIMAL(15,2),
    total_trades INTEGER,
    
    -- API usage
    tokens_used INTEGER,
    api_cost DECIMAL(10,4),
    processing_time_ms INTEGER,
    
    -- Additional data
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Constraints
    CONSTRAINT valid_confidence CHECK (confidence_score BETWEEN 0 AND 1),
    CONSTRAINT valid_tokens CHECK (tokens_used > 0),
    CONSTRAINT valid_win_rate CHECK (win_rate BETWEEN 0 AND 100)
);

-- ============================================================================
-- NOTIFICATIONS TABLE
-- ============================================================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    
    -- Notification details
    channel notification_channel NOT NULL,
    recipient TEXT NOT NULL,
    
    -- Status tracking
    status notification_status DEFAULT 'pending' NOT NULL,
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Message content
    message_id TEXT, -- External message ID (Telegram, email)
    message_content TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Constraints
    CONSTRAINT valid_retry CHECK (retry_count >= 0 AND retry_count <= max_retries)
);

-- ============================================================================
-- SYSTEM LOGS TABLE (for debugging and monitoring)
-- ============================================================================
CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Log details
    service_name VARCHAR(100) NOT NULL,
    log_level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    
    -- Context
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    user_id TEXT,
    correlation_id UUID,
    
    -- Additional data
    metadata JSONB DEFAULT '{}'::jsonb,
    stack_trace TEXT,
    
    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Reports indexes
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX idx_reports_status ON reports(status) WHERE status != 'completed';
CREATE INDEX idx_reports_email_received ON reports(email_received_at DESC);
CREATE INDEX idx_reports_email_from ON reports(email_from);
CREATE INDEX idx_reports_url ON reports USING hash(report_url);

-- Full-text search on report content
CREATE INDEX idx_reports_content_search ON reports USING gin(to_tsvector('english', raw_content));

-- Images indexes
CREATE INDEX idx_images_report_id ON report_images(report_id);
CREATE INDEX idx_images_hash ON report_images(image_hash) WHERE image_hash IS NOT NULL;
CREATE INDEX idx_images_sequence ON report_images(report_id, sequence_order);

-- Analyses indexes
CREATE INDEX idx_analyses_report_id ON analyses(report_id);
CREATE INDEX idx_analyses_created_at ON analyses(created_at DESC);
CREATE INDEX idx_analyses_sentiment ON analyses(sentiment) WHERE sentiment IS NOT NULL;
CREATE INDEX idx_analyses_provider ON analyses(ai_provider);

-- GIN index for JSONB key_trades
CREATE INDEX idx_analyses_key_trades ON analyses USING gin(key_trades);

-- Notifications indexes
CREATE INDEX idx_notifications_analysis_id ON notifications(analysis_id);
CREATE INDEX idx_notifications_status ON notifications(status) WHERE status != 'sent';
CREATE INDEX idx_notifications_channel ON notifications(channel);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- System logs indexes
CREATE INDEX idx_logs_created_at ON system_logs(created_at DESC);
CREATE INDEX idx_logs_service ON system_logs(service_name);
CREATE INDEX idx_logs_level ON system_logs(log_level);
CREATE INDEX idx_logs_report_id ON system_logs(report_id) WHERE report_id IS NOT NULL;

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for reports table
CREATE TRIGGER update_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for notifications table
CREATE TRIGGER update_notifications_updated_at
    BEFORE UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to set processed_at when status becomes completed
CREATE OR REPLACE FUNCTION set_processed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        NEW.processed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic processed_at
CREATE TRIGGER set_report_processed_at
    BEFORE UPDATE ON reports
    FOR EACH ROW
    EXECUTE FUNCTION set_processed_at();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View for complete report information with analysis
CREATE VIEW vw_reports_with_analysis AS
SELECT 
    r.id,
    r.email_received_at,
    r.email_subject,
    r.report_url,
    r.status,
    r.created_at,
    r.processed_at,
    a.id as analysis_id,
    a.ai_provider,
    a.summary,
    a.sentiment,
    a.confidence_score,
    a.key_trades,
    COUNT(ri.id) as image_count,
    COUNT(n.id) as notification_count,
    COUNT(n.id) FILTER (WHERE n.status = 'sent') as notifications_sent
FROM reports r
LEFT JOIN analyses a ON r.id = a.report_id
LEFT JOIN report_images ri ON r.id = ri.report_id
LEFT JOIN notifications n ON a.id = n.analysis_id
GROUP BY r.id, a.id;

-- View for notification statistics
CREATE VIEW vw_notification_stats AS
SELECT 
    channel,
    status,
    COUNT(*) as count,
    AVG(retry_count) as avg_retries,
    MAX(created_at) as last_notification
FROM notifications
GROUP BY channel, status;

-- View for daily report processing metrics
CREATE VIEW vw_daily_metrics AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_reports,
    COUNT(*) FILTER (WHERE status = 'completed') as completed,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    AVG(EXTRACT(EPOCH FROM (processed_at - created_at))) as avg_processing_time_seconds
FROM reports
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- ============================================================================
-- COMMENTS (Documentation)
-- ============================================================================

COMMENT ON TABLE reports IS 'Stores trading report metadata and raw content';
COMMENT ON TABLE report_images IS 'Stores images extracted from trading reports';
COMMENT ON TABLE analyses IS 'Stores AI-generated analysis of trading reports';
COMMENT ON TABLE notifications IS 'Tracks notification delivery status';
COMMENT ON TABLE system_logs IS 'System-wide logging for debugging and monitoring';

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant permissions to trading_user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO trading_user;

-- ============================================================================
-- INITIAL DATA (Optional)
-- ============================================================================

-- Insert a test record (commented out for production)
-- INSERT INTO reports (email_subject, email_from, report_url, status)
-- VALUES ('Test Report', 'test@example.com', 'https://example.com/report/1', 'pending');

-- ============================================================================
-- MAINTENANCE QUERIES
-- ============================================================================

-- Cleanup old logs (run periodically)
-- DELETE FROM system_logs WHERE created_at < NOW() - INTERVAL '30 days';

-- Vacuum and analyze
VACUUM ANALYZE;
