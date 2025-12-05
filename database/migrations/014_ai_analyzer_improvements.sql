-- Add extended thinking support, flexible operations tracking, and new provider support
-- Implements support for extended thinking tokens, thinking content storage,
-- operations_found flag for flexible operations tracking, and expanded provider list

BEGIN;

-- Add new columns for extended thinking support
ALTER TABLE analyses
ADD COLUMN thinking_budget_tokens INTEGER DEFAULT 5000 NOT NULL,
ADD COLUMN thinking_tokens_used INTEGER,
ADD COLUMN thinking_content TEXT;

-- Add operations_found flag for tracking whether trading operations were extracted
ALTER TABLE analyses
ADD COLUMN operations_found BOOLEAN DEFAULT false NOT NULL;

-- Backfill existing records with appropriate defaults
-- Legacy records are treated as having operations (backward compatibility)
UPDATE analyses
SET
    thinking_budget_tokens = 5000,
    thinking_tokens_used = NULL,
    thinking_content = NULL,
    operations_found = true
WHERE operations_found IS NULL;

-- Remove CHECK constraint to allow new provider types (google, fallback, hybrid, etc.)
ALTER TABLE analyses
DROP CONSTRAINT IF EXISTS valid_provider;

-- Expand ai_provider column to support new providers and future extensions
ALTER TABLE analyses
ALTER COLUMN ai_provider TYPE VARCHAR(100);

-- Add comment explaining the flexibility of provider field
COMMENT ON COLUMN analyses.ai_provider IS 'Provider used for analysis: anthropic, groq, google, fallback_keyword, or other. Flexible to support future providers.';

-- Create index on operations_found for efficient filtering
-- Useful for queries like "SELECT * FROM analyses WHERE operations_found = true"
CREATE INDEX IF NOT EXISTS idx_analyses_operations_found
ON analyses(operations_found)
WHERE operations_found = true;

-- Create index on thinking_tokens_used for cost analysis and efficiency tracking
-- Descending order helps queries sorting by highest thinking token usage
CREATE INDEX IF NOT EXISTS idx_analyses_thinking_tokens
ON analyses(thinking_tokens_used DESC NULLS LAST);

-- Create index on ai_provider for provider-specific queries and analytics
CREATE INDEX IF NOT EXISTS idx_analyses_ai_provider
ON analyses(ai_provider);

-- Create GIN index on key_trades JSONB for efficient JSON queries
-- Useful for future queries on specific operation fields within JSONB
CREATE INDEX IF NOT EXISTS idx_analyses_operations_jsonb
ON analyses USING GIN(key_trades);

COMMIT;
