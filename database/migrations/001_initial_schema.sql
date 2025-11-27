-- Initial Database Schema Migration
-- Creates the base schema with reports, analyses, notifications, and system_logs tables

BEGIN;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
CREATE TYPE report_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE notification_channel AS ENUM ('telegram', 'email');
CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'failed', 'retrying');
CREATE TYPE ai_provider AS ENUM ('anthropic', 'groq');
CREATE TYPE sentiment AS ENUM ('bullish', 'bearish', 'neutral', 'mixed');

-- Reports table
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_received_at TIMESTAMPTZ NOT NULL,
    email_subject TEXT,
    email_from TEXT,
    email_message_id TEXT UNIQUE,
    report_url TEXT NOT NULL,
    report_title TEXT,
    raw_content TEXT,
    status report_status DEFAULT 'pending' NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMPTZ,
    credential_id UUID,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    processed_at TIMESTAMPTZ,
    CONSTRAINT valid_url CHECK (report_url ~* '^https?://'),
    CONSTRAINT valid_retry CHECK (retry_count >= 0)
);

-- Report images table
CREATE TABLE IF NOT EXISTS report_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    image_url TEXT,
    image_data BYTEA,
    image_hash TEXT,
    image_type VARCHAR(50) DEFAULT 'screenshot',
    mime_type VARCHAR(100),
    width INTEGER,
    height INTEGER,
    size_bytes INTEGER,
    sequence_order INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT image_source_check CHECK ((image_url IS NOT NULL) OR (image_data IS NOT NULL)),
    CONSTRAINT valid_dimensions CHECK ((width IS NULL AND height IS NULL) OR (width > 0 AND height > 0))
);

-- Analyses table
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    ai_provider ai_provider NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    prompt_template TEXT,
    summary TEXT NOT NULL,
    key_trades JSONB DEFAULT '[]'::jsonb,
    market_analysis TEXT,
    recommendations TEXT,
    sentiment sentiment,
    confidence_score DECIMAL(3,2),
    win_rate DECIMAL(5,2),
    profit_loss DECIMAL(15,2),
    total_trades INTEGER,
    tokens_used INTEGER,
    api_cost DECIMAL(10,4),
    processing_time_ms INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT valid_confidence CHECK (confidence_score BETWEEN 0 AND 1),
    CONSTRAINT valid_tokens CHECK (tokens_used > 0),
    CONSTRAINT valid_win_rate CHECK (win_rate BETWEEN 0 AND 100)
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    channel notification_channel NOT NULL,
    recipient TEXT NOT NULL,
    status notification_status DEFAULT 'pending' NOT NULL,
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    message_id TEXT,
    message_content TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT valid_retry CHECK (retry_count >= 0 AND retry_count <= max_retries)
);

-- System logs table
CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(100) NOT NULL,
    log_level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    user_id TEXT,
    correlation_id UUID,
    metadata JSONB DEFAULT '{}'::jsonb,
    stack_trace TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMIT;
