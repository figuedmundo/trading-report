# Trading Report System - Configuration Setup Guide

This guide walks you through configuring each component of the Trading Report system for your environment.

## Prerequisites

- Docker and Docker Compose installed
- A domain name or local IP address accessible to all services
- Email account for SMTP (Gmail, Outlook, etc.)
- Telegram Bot Token (optional but recommended)
- AI API key (Anthropic Claude or Groq)

## Step 1: AI Provider Setup

**Note**: The settings below define the **default** provider. You can override this per-request using API headers (e.g., `X-AI-Provider`).

### Option A: Anthropic Claude (Recommended)

1. Visit https://console.anthropic.com/
2. Sign up or log in to your account
3. Navigate to **API Keys**
4. Click **Create Key**
5. Copy the key and add to `.env`:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### Option B: Groq (Fast & Cost-Effective)

1. Visit https://console.groq.com/
2. Sign up or log in
3. Navigate to **API Keys**
4. Create a new API key
5. Copy and add to `.env`:
   ```bash
   GROQ_API_KEY=gsk-xxxxxxxxxxxxxxxxxxxxx
   ```

## Step 2: Database Setup

1. Generate secure passwords:
   ```bash
   # Generate random passwords
   openssl rand -base64 32
   ```

2. Add to `.env`:
   ```bash
   POSTGRES_PASSWORD=your_secure_postgres_password
   N8N_DB_PASSWORD=your_n8n_secure_password
   TRADING_USER_PASSWORD=your_trading_app_password
   ```

3. Verify database will start:
   ```bash
   docker-compose up postgres
   # Wait for "database system is ready to accept connections"
   ```

## Step 3: Email/SMTP Configuration

### Gmail Setup (Recommended)

1. Enable 2-Step Verification on your Google Account:
   - Go to https://myaccount.google.com/
   - Click **Security** in the left menu
   - Enable **2-Step Verification**

2. Create an App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Select **Mail** and **Windows Computer** (or your OS)
   - Google generates a 16-character password
   - Copy this password (spaces will be removed automatically)

3. Add to `.env`:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your_16_char_app_password
   SENDER_EMAIL=your-email@gmail.com
   ```

### Outlook Setup

1. Add to `.env`:
   ```bash
   SMTP_HOST=smtp-mail.outlook.com
   SMTP_PORT=587
   SMTP_USER=your-email@outlook.com
   SMTP_PASSWORD=your_outlook_password
   SENDER_EMAIL=your-email@outlook.com
   ```

### Custom SMTP Server

1. Obtain SMTP credentials from your email provider
2. Add to `.env`:
   ```bash
   SMTP_HOST=mail.yourdomain.com
   SMTP_PORT=587
   SMTP_USER=your_username
   SMTP_PASSWORD=your_password
   SENDER_EMAIL=no-reply@yourdomain.com
   ```

## Step 4: Telegram Configuration (Optional)

### Create Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow prompts to create bot (name and username)
4. BotFather sends you a token: `123456789:ABCDefGhIjKlmNoPqRsTuVwXyZ`
5. Copy this token to `.env`:
   ```bash
   TELEGRAM_BOT_TOKEN=123456789:ABCDefGhIjKlmNoPqRsTuVwXyZ
   ```

### Get Your Telegram Chat ID

1. Start a conversation with your bot (search for its username)
2. Send any message to the bot
3. Visit this URL in your browser (replace token):
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
4. Find the `"chat"` object and copy the `"id"` field
5. Add to `.env`:
   ```bash
   TELEGRAM_CHAT_ID=1234567890
   ```

### Test Bot Connection

```bash
# Test that the bot is accessible
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"

# Should return something like:
# {"ok":true,"result":{"id":123456789,"is_bot":true,"first_name":"YourBotName"}}
```

## Step 5: Webhook Security Configuration

Generate secure keys:

```bash
# Generate webhook secret
openssl rand -base64 32

# Generate N8N encryption key
openssl rand -base64 32
```

Add to `.env`:
```bash
WEBHOOK_SECRET_KEY=your_secure_webhook_secret_key
N8N_ENCRYPTION_KEY=your_secure_n8n_encryption_key
```

## Step 6: Network & Domain Configuration

### Local Network Setup (Homelab)

1. Edit `.env`:
   ```bash
   N8N_HOST=localhost
   N8N_PROTOCOL=http
   WEBHOOK_URL=http://localhost:5678/webhook
   ```

2. Services accessible at:
   - N8N: http://localhost:5678
   - Health Monitoring: http://localhost:8003
   - Notification Service: http://localhost:8004

### Public Domain Setup

1. Set up your domain (e.g., `trading.yourdomain.com`)
2. Edit `.env`:
   ```bash
   N8N_HOST=trading.yourdomain.com
   N8N_PROTOCOL=https
   WEBHOOK_URL=https://trading.yourdomain.com/webhook
   ```

3. Use reverse proxy (Nginx/Traefik) for HTTPS:
   ```nginx
   # Example Nginx config
   server {
       listen 443 ssl http2;
       server_name trading.yourdomain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:5678;
       }

       location /webhook {
           proxy_pass http://localhost:8001/webhook;
       }
   }
   ```

## Step 7: Trading Portal Credentials

1. Identify your trading portal login URL
2. Test login manually to verify credentials work
3. Add to `.env`:
   ```bash
   TRADING_PORTAL_USERNAME=your_username
   TRADING_PORTAL_PASSWORD=your_password
   ```

**Security Note**: These credentials are stored in PostgreSQL. Verify your `.env` file is in `.gitignore`.

## Step 8: Verify Configuration

Create a test file to validate all variables are set:

```bash
#!/bin/bash
# test-config.sh

required_vars=(
    "ANTHROPIC_API_KEY"
    "POSTGRES_PASSWORD"
    "SMTP_HOST"
    "SMTP_USER"
    "SMTP_PASSWORD"
    "TELEGRAM_BOT_TOKEN"
    "TELEGRAM_CHAT_ID"
    "WEBHOOK_SECRET_KEY"
    "TRADING_PORTAL_USERNAME"
    "TRADING_PORTAL_PASSWORD"
)

source .env

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing: $var"
    else
        echo "✅ Set: $var"
    fi
done
```

Run the test:
```bash
chmod +x test-config.sh
./test-config.sh
```

## Step 9: Start Services

1. Build images:
   ```bash
   docker-compose build
   ```

2. Start all services:
   ```bash
   docker-compose up -d
   ```

3. Wait for services to be healthy:
   ```bash
   # Check health of all services
   curl http://localhost:8003/api/v1/health/status
   ```

## Step 10: Configure N8N Workflow

### Access N8N Dashboard

- Navigate to http://localhost:5678 (or your domain)
- Create initial user account
- Create workflow following the examples in `/docs/n8n-workflows/`

### Set Up Email Webhook

1. In N8N, create new workflow
2. Add **Webhook** node:
   - Method: `POST`
   - Path: `/webhook/trading-reports`
   - Authentication: None (webhook service validates signature)

3. Test webhook:
   ```bash
   curl -X POST http://localhost:8001/webhook \
     -H "Content-Type: application/json" \
     -H "X-Webhook-Signature: $(echo -n 'test' | openssl dgst -sha256 -mac HMAC -macopt key:${WEBHOOK_SECRET_KEY} | cut -d' ' -f2)" \
     -d '{"from":"test@example.com","subject":"Test Report","body":"Check https://portal.example.com/report/123"}'
   ```

## Configuration Checklist

- [ ] AI API key configured and tested
- [ ] Database passwords generated and set
- [ ] SMTP credentials configured
- [ ] Telegram Bot created and Chat ID obtained
- [ ] Webhook secret keys generated
- [ ] Domain/host configuration set
- [ ] Trading portal credentials verified
- [ ] All Docker images built
- [ ] Services starting successfully
- [ ] Health check endpoint returns 200 OK
- [ ] N8N dashboard accessible
- [ ] Webhook test passes

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs -f

# Rebuild images
docker-compose down -v
docker-compose build
docker-compose up
```

### Webhook not receiving emails
```bash
# Test webhook endpoint
curl -X POST http://localhost:8001/webhook \
  -H "Content-Type: application/json" \
  -d '{"from":"test@example.com","subject":"Test","body":"https://example.com"}'

# Check email webhook logs
docker-compose logs -f email-webhook
```

### SMTP not working
```bash
# Test SMTP connection
python3 -c "
import smtplib
server = smtplib.SMTP('${SMTP_HOST}', ${SMTP_PORT})
server.starttls()
server.login('${SMTP_USER}', '${SMTP_PASSWORD}')
print('SMTP OK')
"
```

### AI Analysis failing
```bash
# Test AI API
curl -X POST http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"content":"Test content","title":"Test Title"}'
```

## Support

For additional help:
- Check `/USERS_MANUAL.md` for usage guide
- Review `/HEALTH_MONITORING.md` for troubleshooting
- Check service logs: `make logs-service SERVICE=<name>`
- Test health: `curl http://localhost:8003/api/v1/health/status`
