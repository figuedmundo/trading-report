-- Database health check
-- Run this query to verify database connectivity and basic health

-- 1. PostgreSQL Version
SELECT 'PostgreSQL Version' as check_name, version() as result;

-- 2. Database Connection
SELECT 'Database Connection' as check_name, 'Connected successfully' as result;

-- 3. Table counts
SELECT
    'Tables' as check_name,
    CONCAT(COUNT(*), ' tables exist') as result
FROM information_schema.tables
WHERE table_schema = 'public';

-- 4. Views
SELECT
    'Views' as check_name,
    CONCAT(COUNT(*), ' views exist') as result
FROM pg_views
WHERE schemaname = 'public';

-- 5. Indexes
SELECT
    'Indexes' as check_name,
    CONCAT(COUNT(*), ' indexes exist') as result
FROM pg_indexes
WHERE schemaname = 'public';

-- 6. Report records
SELECT
    'Reports Table' as check_name,
    CONCAT(COUNT(*), ' records') as result
FROM reports;

-- 7. Report status distribution
SELECT
    'Report Statuses' as check_name,
    CONCAT(
        pending, ' pending, ',
        processing, ' processing, ',
        completed, ' completed, ',
        failed, ' failed'
    ) as result
FROM (
    SELECT
        COUNT(*) FILTER (WHERE status = 'pending') as pending,
        COUNT(*) FILTER (WHERE status = 'processing') as processing,
        COUNT(*) FILTER (WHERE status = 'completed') as completed,
        COUNT(*) FILTER (WHERE status = 'failed') as failed
    FROM reports
) status_counts;

-- 8. Oldest pending report
SELECT
    'Oldest Pending' as check_name,
    CONCAT(
        'Age: ',
        EXTRACT(EPOCH FROM (NOW() - created_at))::integer / 3600,
        ' hours'
    ) as result
FROM reports
WHERE status = 'pending'
ORDER BY created_at ASC
LIMIT 1;

-- 9. Notification delivery success rate
SELECT
    'Notification Success Rate' as check_name,
    CONCAT(
        ROUND(100.0 * sent_count / total_count, 2), '%'
    ) as result
FROM (
    SELECT
        COUNT(*) as total_count,
        COUNT(*) FILTER (WHERE status = 'sent') as sent_count
    FROM notifications
    WHERE created_at > NOW() - INTERVAL '7 days'
) notification_stats;

-- 10. Database size
SELECT
    'Database Size' as check_name,
    pg_size_pretty(pg_database_size(current_database())) as result;
