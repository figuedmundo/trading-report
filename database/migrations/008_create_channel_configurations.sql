-- Migration: Create channel_configurations table (runtime configuration)
-- Date: 2025-11-27
-- Purpose: Store channel-specific configuration (rate limits, timeouts, etc.)

BEGIN;

-- Create channel_configurations table
CREATE TABLE channel_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_name VARCHAR(50) NOT NULL,  -- 'email', 'telegram', 'sms', etc.
    is_enabled BOOLEAN DEFAULT true,
    setting_key VARCHAR(100) NOT NULL,  -- 'rate_limit_per_hour', 'timeout_seconds', etc.
    setting_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create unique constraint on (channel_name, setting_key)
CREATE UNIQUE INDEX idx_channel_config_unique ON channel_configurations(channel_name, setting_key);

-- Create index on channel_name for efficient lookups
CREATE INDEX idx_channel_config_channel_name ON channel_configurations(channel_name);

-- Insert sample configuration data for email channel
INSERT INTO channel_configurations (channel_name, setting_key, setting_value, description) VALUES
  ('email', 'rate_limit_per_hour', '100', 'Max emails per hour'),
  ('email', 'smtp_timeout_seconds', '10', 'SMTP connection timeout in seconds'),
  ('email', 'max_retries', '5', 'Maximum number of retry attempts'),
  ('email', 'is_enabled', 'true', 'Enable/disable email channel');

-- Insert sample configuration data for telegram channel
INSERT INTO channel_configurations (channel_name, setting_key, setting_value, description) VALUES
  ('telegram', 'rate_limit_per_minute', '30', 'Max Telegram messages per minute'),
  ('telegram', 'api_timeout_seconds', '5', 'Telegram API timeout in seconds'),
  ('telegram', 'max_retries', '5', 'Maximum number of retry attempts'),
  ('telegram', 'is_enabled', 'true', 'Enable/disable Telegram channel');

COMMIT;
