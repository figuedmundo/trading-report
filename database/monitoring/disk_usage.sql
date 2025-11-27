-- Disk usage and table size monitoring
-- Track database and table sizes to plan for storage

-- Database size
SELECT
    'Total Database Size' as metric,
    pg_size_pretty(pg_database_size(current_database())) as size;

-- Table sizes (largest first)
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index sizes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Row count and size per row
SELECT
    schemaname,
    tablename,
    n_live_tup as row_count,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    ROUND(pg_total_relation_size(schemaname||'.'||tablename)::numeric / NULLIF(n_live_tup, 0), 2) as bytes_per_row
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;

-- Dead rows (bloat analysis)
SELECT
    schemaname,
    tablename,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_percentage
FROM pg_stat_user_tables
WHERE schemaname = 'public'
    AND n_dead_tup > 0
ORDER BY n_dead_tup DESC;

-- Reports table size growth over time (estimate)
SELECT
    COUNT(*) as total_reports,
    pg_size_pretty(pg_total_relation_size('reports')) as table_size,
    ROUND(pg_total_relation_size('reports')::numeric / NULLIF(COUNT(*), 0), 2) as bytes_per_report
FROM reports;

-- Projected growth (if linear)
SELECT
    COUNT(*) as current_report_count,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 day') as reports_per_day,
    ROUND(COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 day') * 365) as projected_annual,
    ROUND(COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 day') * 365 * 365) as projected_in_10_years
FROM reports;
