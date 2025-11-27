-- Database maintenance: Archive old system logs
-- This script moves logs older than 30 days to an archive table
-- Run this daily or weekly via cron for log retention management

-- Note: system_logs_archive table may need to be created first if not exists
-- CREATE TABLE IF NOT EXISTS system_logs_archive AS SELECT * FROM system_logs WHERE 1=0;

-- Archive logs older than 30 days (configurable)
INSERT INTO system_logs_archive
SELECT * FROM system_logs
WHERE created_at < NOW() - INTERVAL '30 days';

-- Delete archived logs from active table
DELETE FROM system_logs
WHERE created_at < NOW() - INTERVAL '30 days';

-- Analyze table after bulk delete
ANALYZE system_logs;

-- Show archival statistics
SELECT
    'Logs archived' as operation,
    COUNT(*) as count
FROM system_logs_archive
WHERE created_at > NOW() - INTERVAL '1 day'
UNION ALL
SELECT
    'Active logs remaining' as operation,
    COUNT(*) as count
FROM system_logs;
