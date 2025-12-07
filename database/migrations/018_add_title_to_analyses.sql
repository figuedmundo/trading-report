-- Migration: Add title column to analyses table
-- Date: 2025-12-07
-- Description: Adds a title column to store the report title extracted by the scraper.

ALTER TABLE analyses
ADD COLUMN IF NOT EXISTS title TEXT;
