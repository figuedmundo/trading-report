-- Active connection monitoring
-- Track connection pool usage and connection statistics

-- Current active connections
SELECT
    usename as username,
    COUNT(*) as connection_count,
    state,
    ARRAY_AGG(application_name) as applications
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY usename, state
ORDER BY connection_count DESC;

-- Connection details
SELECT
    pid,
    usename,
    application_name,
    state,
    state_change,
    wait_event_type,
    wait_event,
    query_start,
    EXTRACT(EPOCH FROM (NOW() - query_start))::integer as query_seconds
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY query_start DESC;

-- Max connections and usage
SELECT
    'Max Connections' as metric,
    setting as value
FROM pg_settings
WHERE name = 'max_connections'
UNION ALL
SELECT
    'Current Connections',
    COUNT(*)::text
FROM pg_stat_activity
WHERE datname = current_database()
UNION ALL
SELECT
    'Connection Usage %',
    ROUND(100.0 * COUNT(*) / (SELECT setting::integer FROM pg_settings WHERE name = 'max_connections'), 2)::text
FROM pg_stat_activity
WHERE datname = current_database();

-- Idle connections
SELECT
    usename,
    application_name,
    state,
    COUNT(*) as count,
    EXTRACT(EPOCH FROM (NOW() - MAX(state_change)))::integer as idle_seconds_max
FROM pg_stat_activity
WHERE datname = current_database()
    AND state = 'idle'
GROUP BY usename, application_name, state
ORDER BY count DESC;

-- Long-running queries
SELECT
    pid,
    usename,
    application_name,
    query_start,
    EXTRACT(EPOCH FROM (NOW() - query_start))::integer as query_seconds,
    SUBSTRING(query, 1, 100) as query_snippet
FROM pg_stat_activity
WHERE datname = current_database()
    AND query_start IS NOT NULL
    AND EXTRACT(EPOCH FROM (NOW() - query_start)) > 60  -- Queries running >60 seconds
ORDER BY query_start ASC;

-- Connection trends by hour (if pg_stat_statements is enabled)
SELECT
    EXTRACT(HOUR FROM query_start)::integer as hour,
    COUNT(*) as queries
FROM pg_stat_activity
WHERE query_start > NOW() - INTERVAL '24 hours'
GROUP BY EXTRACT(HOUR FROM query_start)
ORDER BY hour DESC;
