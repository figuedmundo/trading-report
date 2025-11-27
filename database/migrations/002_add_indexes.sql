-- Add Indexes Migration
-- Creates indexes for common query patterns

BEGIN;

-- Reports indexes
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status) WHERE status != 'completed';
CREATE INDEX IF NOT EXISTS idx_reports_email_received ON reports(email_received_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_email_from ON reports(email_from);
CREATE INDEX IF NOT EXISTS idx_reports_url ON reports USING hash(report_url);

-- Full-text search on report content
CREATE INDEX IF NOT EXISTS idx_reports_content_search ON reports USING gin(to_tsvector('english', raw_content));

-- Images indexes
CREATE INDEX IF NOT EXISTS idx_images_report_id ON report_images(report_id);
CREATE INDEX IF NOT EXISTS idx_images_hash ON report_images(image_hash) WHERE image_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_images_sequence ON report_images(report_id, sequence_order);

-- Analyses indexes
CREATE INDEX IF NOT EXISTS idx_analyses_report_id ON analyses(report_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_sentiment ON analyses(sentiment) WHERE sentiment IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_analyses_provider ON analyses(ai_provider);

-- GIN index for JSONB key_trades
CREATE INDEX IF NOT EXISTS idx_analyses_key_trades ON analyses USING gin(key_trades);

-- Notifications indexes
CREATE INDEX IF NOT EXISTS idx_notifications_analysis_id ON notifications(analysis_id);
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status) WHERE status != 'sent';
CREATE INDEX IF NOT EXISTS idx_notifications_channel ON notifications(channel);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);

-- System logs indexes
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON system_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_service ON system_logs(service_name);
CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_logs_report_id ON system_logs(report_id) WHERE report_id IS NOT NULL;

COMMIT;
