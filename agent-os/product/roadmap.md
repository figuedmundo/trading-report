# Product Roadmap

## Phase 1: MVP - Core Email-to-Report Pipeline

1. [x] Email Webhook Service & Email Parsing - Set up webhook endpoint to receive email payloads from email service provider, parse email headers/body to extract trading report indicators (keywords, sender, subject patterns), and extract URLs for portal access. `M`

2. [x] Secure Credential Storage & Management - Implement encrypted credential vault for trading portal username/password; support per-report credential overrides; ensure credentials never logged or exposed in system output. `S`

3. [x] Playwright Browser Automation - Build Playwright automation to handle trading portal login, navigate to provided URL, and maintain session state across multiple page interactions. `M`

4. [x] Report Content Extraction & Scraping - Extract text, images, and metadata from trading report pages; handle dynamic content loading; capture TradingView charts and embedded media; store raw HTML and extracted text. `L`

5. [x] PostgreSQL Schema & Data Persistence - Design and implement database schema for storing reports (raw content, extracted text, metadata, source info), report versions, processing status, and audit logs. `S`

6. [x] AI Report Analysis with Groq/Anthropic API - Integrate with chosen AI provider to analyze extracted report text; generate executive summaries (200-300 words); extract key trading signals, symbols, and recommendations. `M`

7. [x] Email Notification Service - Build email formatter and SMTP integration to send AI-analyzed report summaries via email; include original source link, timestamp, and confidence metrics. `S` (Unified Notification Service)

8. [x] Telegram Notification Service - Implement Telegram bot integration to send formatted message summaries with quick links and trading signal highlights; handle emoji formatting for readability. `S` (Unified Notification Service)

9. [x] Webhook Endpoint Security & Rate Limiting - Implement request signing/validation, IP whitelisting, rate limiting, and DDoS protection for the exposed webhook endpoint in homelab environment. `S`

10. [x] Basic Health Monitoring & Error Logging - Add system health checks, error tracking, notification delivery confirmation, and basic alerting for failures (failed logins, extraction errors, API timeouts). `S`

11. [ ] Users Manual - Complete users manual about how to configure all services and n8n, how to use the system, how to troubleshoot, etc. `S`
