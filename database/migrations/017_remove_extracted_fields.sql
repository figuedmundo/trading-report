-- Migration: Remove extracted fields from analyses table
-- Date: 2025-12-07
-- Description: Removes summary, key_trades (trading_signals), and other extracted fields to reduce noise.

-- Drop indexes first
DROP INDEX IF EXISTS idx_analyses_key_trades;
DROP INDEX IF EXISTS idx_analyses_operations_jsonb;
DROP INDEX IF EXISTS idx_analyses_sentiment;

-- Remove columns
ALTER TABLE analyses
    DROP COLUMN IF EXISTS summary,
    DROP COLUMN IF EXISTS key_trades,
    DROP COLUMN IF EXISTS market_analysis,
    DROP COLUMN IF EXISTS recommendations,
    DROP COLUMN IF EXISTS sentiment,
    DROP COLUMN IF EXISTS confidence_score,
    DROP COLUMN IF EXISTS win_rate,
    DROP COLUMN IF EXISTS profit_loss,
    DROP COLUMN IF EXISTS total_trades,
    DROP COLUMN IF EXISTS tokens_used,
    DROP COLUMN IF EXISTS api_cost,
    DROP COLUMN IF EXISTS processing_time_ms;

-- Drop sentiment type if it's no longer used
DROP TYPE IF EXISTS sentiment;
