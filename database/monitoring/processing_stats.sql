-- Processing statistics
-- Analyze report processing rates and status distribution

-- Report processing by status (overall)
SELECT
    status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM reports), 2) as percentage
FROM reports
GROUP BY status
ORDER BY count DESC;

-- Daily processing metrics (last 30 days)
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_reports,
    COUNT(*) FILTER (WHERE status = 'completed') as completed,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    COUNT(*) FILTER (WHERE status IN ('pending', 'processing')) as in_progress,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'completed') / COUNT(*), 2) as completion_rate
FROM reports
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Average processing time (completed reports)
SELECT
    ROUND(AVG(EXTRACT(EPOCH FROM (processed_at - created_at)))) as avg_seconds,
    ROUND(MIN(EXTRACT(EPOCH FROM (processed_at - created_at)))) as min_seconds,
    ROUND(MAX(EXTRACT(EPOCH FROM (processed_at - created_at)))) as max_seconds,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (processed_at - created_at)))) as p95_seconds
FROM reports
WHERE processed_at IS NOT NULL
    AND created_at > NOW() - INTERVAL '7 days';

-- Reports by sender (email_from)
SELECT
    email_from,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE status = 'completed') as completed,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    COUNT(*) FILTER (WHERE status = 'pending') as pending
FROM reports
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY email_from
ORDER BY count DESC;

-- Retry analysis
SELECT
    retry_count,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE status = 'completed') as successful,
    COUNT(*) FILTER (WHERE status = 'failed') as failed
FROM reports
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY retry_count
ORDER BY retry_count;

-- Processing duration by status
SELECT
    status,
    COUNT(*) as count,
    ROUND(AVG(EXTRACT(EPOCH FROM (processed_at - created_at)))) as avg_seconds,
    ROUND(MAX(EXTRACT(EPOCH FROM (processed_at - created_at)))) as max_seconds
FROM reports
WHERE processed_at IS NOT NULL
GROUP BY status
ORDER BY count DESC;
