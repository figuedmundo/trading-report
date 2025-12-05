-- Add raw_analysis_response column for storing complete LLM responses
-- This allows storing the full markdown response from any LLM provider
-- without enforcing a specific schema or section names

BEGIN;

-- Add raw_analysis_response column to store complete LLM responses
ALTER TABLE analyses
ADD COLUMN raw_analysis_response TEXT;

-- Add comment explaining the purpose
COMMENT ON COLUMN analyses.raw_analysis_response IS 'Complete markdown response from LLM provider. Stores the raw output as returned, without parsing or section extraction.';

-- Create index on analysis response storage for potential future queries
CREATE INDEX IF NOT EXISTS idx_analyses_response_length
ON analyses(LENGTH(COALESCE(raw_analysis_response, '')));

COMMIT;
