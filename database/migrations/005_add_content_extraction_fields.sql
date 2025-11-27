-- Content Extraction Fields Migration
-- Adds columns for storing extracted clean HTML and image metadata JSONB

BEGIN;

-- Add extracted_text column for clean semantic HTML or fallback text
ALTER TABLE reports
ADD COLUMN IF NOT EXISTS extracted_text TEXT;

-- Add extracted_images column for image metadata JSONB array
ALTER TABLE reports
ADD COLUMN IF NOT EXISTS extracted_images JSONB DEFAULT '[]'::jsonb;

-- Create index on extracted_images for performance on large datasets
CREATE INDEX IF NOT EXISTS idx_reports_extracted_images ON reports USING gin(extracted_images);

-- Create index on extracted_text for full-text search optimization
CREATE INDEX IF NOT EXISTS idx_reports_extracted_text ON reports USING gin(to_tsvector('english', extracted_text));

COMMIT;
