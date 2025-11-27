-- Notification delivery statistics
-- Track success rates and performance of notification channels

-- Overall delivery success rate
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'sent') as sent,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    COUNT(*) FILTER (WHERE status = 'retrying') as retrying,
    COUNT(*) FILTER (WHERE status = 'pending') as pending,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'sent') / COUNT(*), 2) as success_rate
FROM notifications;

-- Success rate by channel
SELECT
    channel,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'sent') as sent,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'sent') / COUNT(*), 2) as success_rate,
    ROUND(AVG(retry_count), 2) as avg_retries
FROM notifications
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY channel
ORDER BY total DESC;

-- Delivery latency (from sent notifications)
SELECT
    channel,
    COUNT(*) as sent_count,
    ROUND(AVG((metadata->>'delivery_latency_ms')::numeric)) as avg_latency_ms,
    ROUND(MIN((metadata->>'delivery_latency_ms')::numeric)) as min_latency_ms,
    ROUND(MAX((metadata->>'delivery_latency_ms')::numeric)) as max_latency_ms
FROM notifications
WHERE status = 'sent'
    AND metadata ? 'delivery_latency_ms'
    AND created_at > NOW() - INTERVAL '7 days'
GROUP BY channel
ORDER BY avg_latency_ms DESC;

-- Failure analysis by channel
SELECT
    channel,
    COUNT(*) as failed_count,
    COUNT(*) as total_failed,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM notifications WHERE status = 'failed' AND created_at > NOW() - INTERVAL '7 days'), 2) as pct_of_total_failures
FROM notifications
WHERE status = 'failed'
    AND created_at > NOW() - INTERVAL '7 days'
GROUP BY channel
ORDER BY failed_count DESC;

-- Notifications by status (last 24 hours)
SELECT
    status,
    channel,
    COUNT(*) as count
FROM notifications
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY status, channel
ORDER BY channel, status;

-- Retry distribution
SELECT
    channel,
    retry_count,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM notifications WHERE created_at > NOW() - INTERVAL '7 days'), 2) as percentage
FROM notifications
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY channel, retry_count
ORDER BY channel, retry_count;

-- Top recipients (email addresses or telegram IDs)
SELECT
    channel,
    recipient,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'sent') as sent,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'sent') / COUNT(*), 2) as success_rate
FROM notifications
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY channel, recipient
ORDER BY total DESC
LIMIT 20;
