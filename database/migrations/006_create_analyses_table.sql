-- Create analyses table for AI analysis results
-- Stores trading signal analysis and AI provider tracking

BEGIN;

-- Create analyses table with JSONB for trading signals
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    trading_signals JSONB DEFAULT '[]'::jsonb,
    ai_provider VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT valid_provider CHECK (ai_provider IN ('anthropic', 'groq', 'fallback_keyword'))
);

-- Create index on report_id for query performance
CREATE INDEX IF NOT EXISTS idx_analyses_report_id ON analyses(report_id);

-- Create index on created_at for sorting
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);

COMMIT;
