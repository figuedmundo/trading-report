# ============================================================================
# Trading Report Automation - Environment Configuration
# ============================================================================
# Copy this file to .env and configure with your actual values
# NEVER commit .env to version control!

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=trading_reports
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=change_this_to_secure_password

# Database connection URL (auto-generated, no need to change)
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# ============================================================================
# N8N CONFIGURATION
# ============================================================================
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=change_this_n8n_password

# N8N Host (your domain or localhost for development)
N8N_HOST=localhost
N8N_PROTOCOL=http  # Use 'https' in production with Traefik
N8N_PORT=5678

# Webhook URL (public URL for email webhooks)
WEBHOOK_URL=http://localhost:5678/webhook  # Change to https://trading-hook.yourdomain.com in production

# ============================================================================
# SERVICE URLS (Internal Docker Network)
# ============================================================================
PLAYWRIGHT_SERVICE_URL=http://playwright-scraper:8000
AI_ANALYZER_SERVICE_URL=http://ai-analyzer:8001
NOTIFICATION_SERVICE_URL=http://notification-service:8002

# ============================================================================
# AI PROVIDERS (Choose one or configure both)
# ============================================================================

# Anthropic (Claude) - Recommended
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Groq (Alternative)
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Default provider (anthropic or groq)
DEFAULT_AI_PROVIDER=anthropic

# ============================================================================
# TELEGRAM CONFIGURATION
# ============================================================================
# Get token from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Get your chat ID from @userinfobot on Telegram
TELEGRAM_CHAT_ID=123456789

# ============================================================================
# EMAIL (SMTP) CONFIGURATION
# ============================================================================
# For Gmail: Use App Password (not your regular password)
# Enable 2FA and create app password at: https://myaccount.google.com/apppasswords

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM=Trading Reports <your-email@gmail.com>

# For other providers:
# Outlook: smtp-mail.outlook.com:587
# Yahoo: smtp.mail.yahoo.com:587
# Custom SMTP: your-smtp-server.com:587

# ============================================================================
# TRADING PORTAL CREDENTIALS
# ============================================================================
# Your credentials for the trading report portal
TRADING_PORTAL_USERNAME=your_portal_username
TRADING_PORTAL_PASSWORD=your_portal_password
TRADING_PORTAL_URL=https://portal.example.com  # Base URL of your trading portal

# ============================================================================
# SECURITY
# ============================================================================
# Generate secure random keys:
# python -c "import secrets; print(secrets.token_urlsafe(32))"

SECRET_KEY=generate_a_secure_random_key_here
API_KEY=generate_another_secure_key_here

# ============================================================================
# APPLICATION SETTINGS
# ============================================================================

# Environment (development, staging, production)
ENVIRONMENT=development

# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Debug mode (true/false)
DEBUG=false

# CORS origins (comma-separated)
CORS_ORIGINS=http://localhost:5678,http://localhost:3000

# ============================================================================
# PLAYWRIGHT SCRAPER SETTINGS
# ============================================================================

# Browser configuration
BROWSER_HEADLESS=true
SCRAPE_TIMEOUT=60000  # milliseconds (60 seconds)
MAX_CONCURRENT_SCRAPES=3

# Screenshot and image settings
ENABLE_SCREENSHOTS=true
IMAGE_QUALITY=80  # JPEG quality (1-100)
MAX_IMAGE_SIZE_MB=5

# Retry configuration
MAX_SCRAPE_RETRIES=3
RETRY_DELAY_SECONDS=5

# ============================================================================
# AI ANALYZER SETTINGS
# ============================================================================

# Token limits
MAX_INPUT_TOKENS=50000
MAX_OUTPUT_TOKENS=4000

# Analysis configuration
ENABLE_DETAILED_ANALYSIS=true
INCLUDE_TRADE_RECOMMENDATIONS=true
EXTRACT_METRICS=true

# Retry configuration
MAX_AI_RETRIES=3
AI_RETRY_DELAY_SECONDS=2

# ============================================================================
# NOTIFICATION SETTINGS
# ============================================================================

# Notification preferences
ENABLE_TELEGRAM=true
ENABLE_EMAIL=true

# Retry configuration
MAX_NOTIFICATION_RETRIES=3
NOTIFICATION_RETRY_DELAY_SECONDS=10

# Rate limiting
TELEGRAM_RATE_LIMIT=30  # messages per minute
EMAIL_RATE_LIMIT=60     # emails per hour

# ============================================================================
# REDIS CONFIGURATION (Caching & Rate Limiting)
# ============================================================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Optional, leave empty if no password

# Cache TTL (seconds)
CACHE_TTL=3600  # 1 hour

# ============================================================================
# TRAEFIK / SSL CONFIGURATION
# ============================================================================

# Let's Encrypt email for SSL certificate
ACME_EMAIL=your-email@example.com

# Domain names
DOMAIN=yourdomain.com
N8N_SUBDOMAIN=n8n.yourdomain.com
WEBHOOK_SUBDOMAIN=trading-hook.yourdomain.com

# ============================================================================
# DATA RETENTION
# ============================================================================

# Automatic cleanup (days)
KEEP_REPORTS_DAYS=90
KEEP_LOGS_DAYS=30
KEEP_IMAGES_DAYS=60

# Archive old data instead of deleting
ENABLE_ARCHIVING=false
ARCHIVE_PATH=/backups/archive

# ============================================================================
# DEVELOPMENT ONLY (Remove in production)
# ============================================================================

# Development settings
DEV_SKIP_AUTH=false  # Skip API key authentication
DEV_MOCK_AI=false   # Use mock AI responses
DEV_FAST_MODE=false  # Reduce timeouts for faster testing

# Test credentials
TEST_REPORT_URL=https://example.com/test-report
TEST_EMAIL_FROM=test@example.com

# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

# Worker configuration
WORKER_PROCESSES=2
WORKER_CONNECTIONS=1000

# Database pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30

# Request timeouts (seconds)
REQUEST_TIMEOUT=60
CONNECT_TIMEOUT=10

# ============================================================================
# TIMEZONE
# ============================================================================
TZ=Europe/Malta  # Change to your timezone
