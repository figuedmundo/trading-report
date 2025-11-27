-- Performance monitoring: Identify slow queries
-- This script helps identify queries that need optimization
-- Requires pg_stat_statements extension to be enabled

-- Prerequisites:
-- 1. Enable in postgresql.conf: shared_preload_libraries = 'pg_stat_statements'
-- 2. CREATE EXTENSION pg_stat_statements;
-- 3. Run periodically (hourly/daily) to find performance issues

-- Find slowest queries by total time
SELECT
    query,
    calls,
    mean_exec_time,
    max_exec_time,
    total_exec_time,
    rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Find most called queries (potential optimization targets)
SELECT
    query,
    calls,
    mean_exec_time,
    total_exec_time
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY calls DESC
LIMIT 20;

-- Find queries with long total execution time
SELECT
    query,
    calls,
    mean_exec_time,
    total_exec_time,
    ROUND(100.0 * total_exec_time / (SELECT SUM(total_exec_time) FROM pg_stat_statements WHERE query NOT LIKE '%pg_stat_statements%'), 2) as pct_of_total
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC
LIMIT 20;
