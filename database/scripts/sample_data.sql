-- Sample data for trading_reports database
-- This file contains realistic test data covering various report statuses and scenarios
-- It is idempotent and safe to re-run

-- Truncate all tables (cascade delete) to ensure clean state
TRUNCATE TABLE notifications CASCADE;
TRUNCATE TABLE analyses CASCADE;
TRUNCATE TABLE report_images CASCADE;
TRUNCATE TABLE system_logs CASCADE;
TRUNCATE TABLE reports CASCADE;

-- ============================================================================
-- SAMPLE REPORTS
-- ============================================================================

-- Report 1: Completed report (full pipeline)
INSERT INTO reports (
    id, email_received_at, email_from, email_subject, email_message_id,
    report_url, report_title, raw_content, status, metadata,
    created_at, updated_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    '2025-11-25 09:30:00+00',
    'reports@xmtrading.com',
    'XAU/USD Trading Report - 2025-11-25',
    '<msg-2025-11-25-001@xmtrading.com>',
    'https://reports.xmtrading.com/reports/20251125',
    'XAU/USD Trading Report - 2025-11-25',
    'Gold market showed bullish momentum today with clean breakout above 2700 level. Strong buying pressure from safe-haven demand. Major resistance now at 2710-2715 level. Recommend monitoring for continuation after pullback testing 2705 support.',
    'completed',
    '{"broker": "XM", "account": "live", "symbols": ["XAUUSD"], "extracted_from": "email_body"}',
    '2025-11-25 09:30:00+00',
    '2025-11-25 09:35:00+00'
);

-- Report 2: Processing report (in scraper stage)
INSERT INTO reports (
    id, email_received_at, email_from, email_subject, email_message_id,
    report_url, status, metadata, created_at, updated_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440001',
    '2025-11-25 10:00:00+00',
    'reports@icmarkets.com',
    'EURUSD Daily Analysis',
    '<msg-2025-11-25-002@icmarkets.com>',
    'https://analysis.icmarkets.com/daily/20251125',
    'processing',
    '{"broker": "IC Markets", "account": "demo", "symbols": ["EURUSD"]}',
    '2025-11-25 10:00:00+00',
    '2025-11-25 10:02:00+00'
);

-- Report 3: Failed report (max retries exceeded)
INSERT INTO reports (
    id, email_received_at, email_from, email_subject, email_message_id,
    report_url, status, error_message, retry_count, last_retry_at,
    metadata, created_at, updated_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440002',
    '2025-11-25 08:00:00+00',
    'reports@oanda.com',
    'GBP/USD Technical Analysis',
    '<msg-2025-11-25-003@oanda.com>',
    'https://analysis.oanda.com/technical/20251125',
    'failed',
    'Login failed: 403 Forbidden (incorrect credentials or temporary lockout)',
    3,
    '2025-11-25 08:45:00+00',
    '{"broker": "OANDA", "account": "live", "symbols": ["GBPUSD"]}',
    '2025-11-25 08:00:00+00',
    '2025-11-25 08:45:00+00'
);

-- Report 4: Pending report (awaiting processing)
INSERT INTO reports (
    id, email_received_at, email_from, email_subject, email_message_id,
    report_url, status, metadata, created_at, updated_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440003',
    '2025-11-25 11:00:00+00',
    'reports@pepperstone.com',
    'Market Update - Oil and Metals',
    '<msg-2025-11-25-004@pepperstone.com>',
    'https://updates.pepperstone.com/market/20251125',
    'pending',
    '{"broker": "Pepperstone", "account": "live", "symbols": ["XAUUSD", "WTIUSD"]}',
    '2025-11-25 11:00:00+00',
    '2025-11-25 11:00:00+00'
);

-- Report 5: Failed with single retry
INSERT INTO reports (
    id, email_received_at, email_from, email_subject, email_message_id,
    report_url, status, error_message, retry_count, last_retry_at,
    metadata, created_at, updated_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440004',
    '2025-11-25 07:00:00+00',
    'reports@dukascopy.com',
    'Daily Forex Report',
    '<msg-2025-11-25-005@dukascopy.com>',
    'https://reports.dukascopy.com/daily/20251125',
    'failed',
    'Network timeout: connection refused',
    1,
    '2025-11-25 07:15:00+00',
    '{"broker": "Dukascopy", "account": "demo"}',
    '2025-11-25 07:00:00+00',
    '2025-11-25 07:15:00+00'
);

-- ============================================================================
-- SAMPLE REPORT IMAGES
-- ============================================================================

-- Images for Report 1 (XAU/USD completed report)
INSERT INTO report_images (
    id, report_id, image_url, image_type, mime_type, width, height,
    sequence_order, metadata, created_at
) VALUES
    ('660e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000',
     'https://reports.xmtrading.com/charts/20251125/xauusd_4h.png',
     'chart', 'image/png', 1024, 768, 0,
     '{"timeframe": "4H", "symbol": "XAUUSD"}',
     '2025-11-25 09:30:00+00'),
    ('660e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000',
     'https://reports.xmtrading.com/charts/20251125/xauusd_1h.png',
     'chart', 'image/png', 1024, 768, 1,
     '{"timeframe": "1H", "symbol": "XAUUSD"}',
     '2025-11-25 09:30:00+00'),
    ('660e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000',
     'https://www.tradingview.com/chart/XAUUSD/?utm_source=xmtrading',
     'tradingview_link', 'text/html', NULL, NULL, 2,
     '{"embedded": true}',
     '2025-11-25 09:30:00+00');

-- Images for Report 2 (EURUSD processing report)
INSERT INTO report_images (
    id, report_id, image_url, image_type, mime_type, width, height,
    sequence_order, metadata, created_at
) VALUES
    ('660e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440001',
     'https://analysis.icmarkets.com/daily/eurusd_daily.png',
     'chart', 'image/png', 1024, 768, 0,
     '{"timeframe": "D1", "symbol": "EURUSD"}',
     '2025-11-25 10:00:00+00');

-- ============================================================================
-- SAMPLE ANALYSES
-- ============================================================================

-- Analysis for Report 1 (XAU/USD completed)
INSERT INTO analyses (
    id, report_id, ai_provider, model_used, prompt_template,
    summary, key_trades, market_analysis, recommendations,
    sentiment, confidence_score, win_rate, profit_loss, total_trades,
    tokens_used, api_cost, processing_time_ms, metadata, created_at
) VALUES (
    '770e8400-e29b-41d4-a716-446655440000',
    '550e8400-e29b-41d4-a716-446655440000',
    'anthropic',
    'claude-3-5-sonnet-20241022',
    'v1-trading-analysis',
    'Gold showed bullish momentum today with clean breakout above 2700 level. Strong safe-haven demand from geopolitical tensions. Primary resistance at 2710-2715 with support at 2705.',
    '[
        {"symbol": "XAUUSD", "entry": 2695.50, "exit": 2708.30, "type": "long", "timeframe": "4H", "profit_loss": 12.80, "status": "closed"},
        {"symbol": "XAUUSD", "entry": 2705.00, "exit": 2712.50, "type": "long", "timeframe": "1H", "profit_loss": 7.50, "status": "closed"},
        {"symbol": "XAUUSD", "entry": 2710.00, "exit": 2715.25, "type": "long", "timeframe": "1H", "profit_loss": 5.25, "status": "open"}
    ]'::jsonb,
    'Gold benefiting from USD weakness and safe-haven flows. Technical structure remains bullish after breaking key resistance levels.',
    'Recommend accumulating on pullbacks toward 2705 support. Set stop-loss below 2700 for trend-following positions.',
    'bullish',
    0.87,
    66.67,
    25.55,
    3,
    1247,
    0.0312,
    2150,
    '{"model_settings": {"temperature": 0.7, "max_tokens": 2000}, "extraction_confidence": 0.95}',
    '2025-11-25 09:35:00+00'
);

-- Analysis for Report 2 would not exist yet since it's in processing status
-- (shown for completeness of completed reports only)

-- ============================================================================
-- SAMPLE NOTIFICATIONS
-- ============================================================================

-- Email and Telegram notifications for Report 1 analysis (completed)
INSERT INTO notifications (
    id, analysis_id, channel, recipient, status, sent_at,
    message_id, message_content, metadata, created_at, updated_at
) VALUES
    ('880e8400-e29b-41d4-a716-446655440000',
     '770e8400-e29b-41d4-a716-446655440000',
     'email',
     'trader@example.com',
     'sent',
     '2025-11-25 09:40:00+00',
     '20251125-094000-smtp@email-service',
     'XAU/USD Report Summary: Bullish momentum, 3 trades identified (2 closed +25.55, 1 open). Sentiment: Bullish (87% confidence). Recommend monitoring 2705 support. Full analysis attached.',
     '{"delivery_latency_ms": 450, "retry_attempts": 0}',
     '2025-11-25 09:35:00+00',
     '2025-11-25 09:40:00+00'),
    ('880e8400-e29b-41d4-a716-446655440001',
     '770e8400-e29b-41d4-a716-446655440000',
     'telegram',
     '123456789',
     'sent',
     '2025-11-25 09:40:00+00',
     '7289473829',
     'XAU/USD: Bullish setup, 3 trades, WR 66.7%, P/L +25.55. Monitor 2705 support.',
     '{"delivery_latency_ms": 230, "retry_attempts": 0}',
     '2025-11-25 09:35:00+00',
     '2025-11-25 09:40:00+00');

-- Pending notifications for Report 2 (processing)
INSERT INTO notifications (
    id, analysis_id, channel, recipient, status, retry_count, max_retries,
    created_at, updated_at
) VALUES
    ('880e8400-e29b-41d4-a716-446655440002',
     '770e8400-e29b-41d4-a716-446655440000',
     'email',
     'trader@example.com',
     'pending',
     0,
     3,
     '2025-11-25 10:05:00+00',
     '2025-11-25 10:05:00+00');

-- ============================================================================
-- SAMPLE SYSTEM LOGS
-- ============================================================================

-- Log entry for Report 1: Scraping completed
INSERT INTO system_logs (
    id, service_name, log_level, message, report_id, correlation_id,
    metadata, created_at
) VALUES (
    '990e8400-e29b-41d4-a716-446655440000',
    'scraper_service',
    'INFO',
    'Report scraping completed successfully',
    '550e8400-e29b-41d4-a716-446655440000',
    '12345678-1234-1234-1234-123456789012',
    '{
        "duration_ms": 3200,
        "login_duration_ms": 1200,
        "content_extraction_ms": 1800,
        "images_found": 3,
        "tradingview_links": 1,
        "content_length_bytes": 45823,
        "page_load_time_ms": 850
    }'::jsonb,
    '2025-11-25 09:31:00+00'
);

-- Log entry for Report 1: Analysis completed
INSERT INTO system_logs (
    id, service_name, log_level, message, report_id, correlation_id,
    metadata, created_at
) VALUES (
    '990e8400-e29b-41d4-a716-446655440001',
    'ai_analyzer',
    'INFO',
    'Report analysis completed',
    '550e8400-e29b-41d4-a716-446655440000',
    '12345678-1234-1234-1234-123456789012',
    '{
        "ai_provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "input_tokens": 847,
        "output_tokens": 400,
        "total_tokens": 1247,
        "api_cost": 0.0312,
        "processing_time_ms": 2150,
        "sentiment": "bullish",
        "confidence": 0.87,
        "key_trades_extracted": 3
    }'::jsonb,
    '2025-11-25 09:33:00+00'
);

-- Log entry for Report 1: Notifications sent
INSERT INTO system_logs (
    id, service_name, log_level, message, report_id, correlation_id,
    metadata, created_at
) VALUES (
    '990e8400-e29b-41d4-a716-446655440002',
    'notification_service',
    'INFO',
    'Analysis notifications sent successfully',
    '550e8400-e29b-41d4-a716-446655440000',
    '12345678-1234-1234-1234-123456789012',
    '{
        "channels_sent": ["email", "telegram"],
        "email_latency_ms": 450,
        "telegram_latency_ms": 230,
        "total_duration_ms": 680
    }'::jsonb,
    '2025-11-25 09:40:00+00'
);

-- Log entry for Report 3: Failure after max retries
INSERT INTO system_logs (
    id, service_name, log_level, message, report_id, correlation_id,
    metadata, stack_trace, created_at
) VALUES (
    '990e8400-e29b-41d4-a716-446655440003',
    'scraper_service',
    'ERROR',
    'Report processing abandoned: max retries exceeded',
    '550e8400-e29b-41d4-a716-446655440002',
    '87654321-4321-4321-4321-210987654321',
    '{
        "retry_count": 3,
        "max_retries": 3,
        "total_duration_hours": 0.75,
        "error": "Login failed: 403 Forbidden",
        "operator_notification_sent": true,
        "portal_url": "https://analysis.oanda.com/technical/20251125"
    }'::jsonb,
    'Traceback (most recent call last):
    File "scraper.py", line 125, in login
        browser.goto(portal_url, {"waitUntil": "networkidle"})
    PlaywrightError: net::ERR_HTTP_RESPONSE_CODE_403
    Response status 403 from https://analysis.oanda.com/login',
    '2025-11-25 08:45:00+00'
);

-- Log entry for Report 2: Scraping in progress
INSERT INTO system_logs (
    id, service_name, log_level, message, report_id, correlation_id,
    metadata, created_at
) VALUES (
    '990e8400-e29b-41d4-a716-446655440004',
    'scraper_service',
    'INFO',
    'Report scraping started',
    '550e8400-e29b-41d4-a716-446655440001',
    '55555555-5555-5555-5555-555555555555',
    '{
        "portal_url": "https://analysis.icmarkets.com/daily/20251125",
        "user_agent": "Mozilla/5.0 (Playwright)"
    }'::jsonb,
    '2025-11-25 10:01:00+00'
);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify sample data
SELECT 'Reports' as table_name, COUNT(*) as row_count FROM reports
UNION ALL
SELECT 'Report Images', COUNT(*) FROM report_images
UNION ALL
SELECT 'Analyses', COUNT(*) FROM analyses
UNION ALL
SELECT 'Notifications', COUNT(*) FROM notifications
UNION ALL
SELECT 'System Logs', COUNT(*) FROM system_logs
ORDER BY 1;
