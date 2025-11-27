-- Operational monitoring: Find stuck reports
-- This query identifies reports that may be stuck in processing or pending states
-- Run daily to detect issues that need manual intervention

-- Reports stuck in processing status for more than 24 hours
SELECT
    id,
    email_from,
    email_subject,
    status,
    created_at,
    updated_at,
    EXTRACT(EPOCH FROM (NOW() - created_at))::integer / 3600 as age_hours,
    EXTRACT(EPOCH FROM (NOW() - updated_at))::integer / 3600 as hours_since_update
FROM reports
WHERE status = 'processing'
    AND created_at < NOW() - INTERVAL '24 hours'
ORDER BY created_at ASC;

-- Reports in pending status for more than 48 hours (likely abandoned)
SELECT
    id,
    email_from,
    email_subject,
    status,
    created_at,
    EXTRACT(EPOCH FROM (NOW() - created_at))::integer / 3600 as age_hours
FROM reports
WHERE status = 'pending'
    AND created_at < NOW() - INTERVAL '48 hours'
ORDER BY created_at ASC;

-- Failed reports with max retries exceeded
SELECT
    id,
    email_from,
    email_subject,
    status,
    retry_count,
    error_message,
    last_retry_at,
    EXTRACT(EPOCH FROM (NOW() - created_at))::integer / 3600 as age_hours
FROM reports
WHERE status = 'failed'
    AND retry_count >= 3
    AND created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;

-- Notifications stuck in retrying status
SELECT
    n.id,
    a.report_id,
    n.channel,
    n.recipient,
    n.status,
    n.retry_count,
    n.max_retries,
    n.created_at,
    n.updated_at,
    EXTRACT(EPOCH FROM (NOW() - n.updated_at))::integer / 3600 as hours_since_update
FROM notifications n
JOIN analyses a ON n.analysis_id = a.id
WHERE n.status = 'retrying'
    AND n.updated_at < NOW() - INTERVAL '24 hours'
ORDER BY n.created_at ASC;

-- Summary of report statuses
SELECT
    status,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as in_last_24h,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as in_last_7d,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as in_last_30d
FROM reports
GROUP BY status
ORDER BY count DESC;
