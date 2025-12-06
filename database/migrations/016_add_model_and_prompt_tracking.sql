-- Add columns for tracking AI model and prompt type
-- This allows granular tracking of which specific model and prompt version were used

BEGIN;

-- Add model_used column if it doesn't exist
ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS model_used VARCHAR(100);

-- Add prompt_type column
ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS prompt_type VARCHAR(100);

-- Add comments
COMMENT ON COLUMN analyses.model_used IS 'Specific AI model version used (e.g., claude-3-5-sonnet-20241022)';
COMMENT ON COLUMN analyses.prompt_type IS 'Type of prompt template used (e.g., default, conservative, detailed)';

-- Create indexes for analytics
CREATE INDEX IF NOT EXISTS idx_analyses_model_used ON analyses(model_used);
CREATE INDEX IF NOT EXISTS idx_analyses_prompt_type ON analyses(prompt_type);

COMMIT;
