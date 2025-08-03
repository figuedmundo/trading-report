# 🤖 Market Report AI Automation System

An intelligent system that automatically processes market report emails, translates content, performs AI analysis, and delivers insights through multiple channels.

## 🎯 Features

- **📧 Email Detection**: Automatic Gmail monitoring via Zapier webhook
- **🕷️ Smart Scraping**: Playwright-based web scraping with login handling
- **🧠 AI Analysis**: Groq AI with Moonshot model for translation & analysis
- **📊 Notion Integration**: Rich formatted reports with structured data
- **📱 Telegram Notifications**: Instant mobile alerts
- **📬 Email Reports**: Comprehensive HTML/text email summaries
- **🛡️ Error Handling**: Comprehensive logging and error notifications

## 🏗️ Architecture

```
Gmail → Zapier → Webhook → Flask API → [Scraper → AI → Notion/Telegram/Email]
```

### Core Components

- `config.py` - Centralized configuration management
- `ai.py` - Groq AI with Moonshot model integration  
- `scraper.py` - Playwright web scraping with smart login
- `extractor.py` - Content extraction and URL parsing
- `notion_client.py` - Rich Notion integration with markdown
- `notifier.py` - Telegram and email notifications
- `routes.py` - Flask API endpoints

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- PythonAnywhere account (or similar Python hosting)
- Groq API key
- Notion integration token
- Telegram bot token
- Gmail account for email notifications

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd market_report_ai

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Set up environment
cp .env.example .env
# Edit .env with your credentials
```

### 3. Configuration

Edit `.env` file with your credentials:

```bash
# Report
PRO_USERNAME=
PRO_PASSWORD=

# Flask Configuration
SECRET_KEY=change-this-to-a-random-secret-key
DEBUG=False
LOG_LEVEL=INFO

# Groq AI Configuration  
GROQ_API_KEY=your-groq-api-key-here

# Notion Configuration
NOTION_API_KEY=secret_your-notion-integration-token
NOTION_DATABASE_ID=your-notion-database-id

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-gmail-app-password
RECIPIENT_EMAIL=your-recipient@gmail.com
```

### 4. Deploy to PythonAnywhere

```bash
# Upload files to PythonAnywhere
# Configure WSGI app pointing to wsgi.py
# Set source code path to your project directory
```

### 5. Set up Zapier Integration

1. Create Zapier account
2. Set up Gmail trigger for new emails
3. Add webhook action pointing to:
   ```
   https://yourusername.pythonanywhere.com/api/webhook/process-report
   ```
4. Configure webhook payload:
   ```json
   {
       "email_html": "{{body_html}}",
       "email_text": "{{body_plain}}",
       "subject": "{{subject}}",
       "from": "{{from}}"
   }
   ```

## 🧪 Testing

### Health Check
```bash
curl https://yourusername.pythonanywhere.com/api/health
```

### Test Individual Components
```bash
# Test scraping
curl -X POST https://yourusername.pythonanywhere.com/api/test-scraper \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Test AI processing
curl -X POST https://yourusername.pythonanywhere.com/api/test-ai \
  -H "Content-Type: application/json" \
  -d '{"content": "Sample market report content..."}'

# Test Notion integration
curl -X POST https://yourusername.pythonanywhere.com/api/test-notion

# Test Telegram notifications
curl -X POST https://yourusername.pythonanywhere.com/api/test-telegram

# Test email notifications
curl -X POST https://yourusername.pythonanywhere.com/api/test-email
```

## 📊 Notion Database Setup

Create a Notion database with these properties:

- **Title** (Title)
- **Source URL** (URL)
- **Date** (Date)
- **Status** (Select: New, Processed, Reviewed)
- **Market Sentiment** (Select: Positive, Negative, Neutral)
- **Word Count** (Number)
- **Quality Score** (Number)
- **Sectors** (Multi-select)
- **Stocks** (Multi-select)

## 🤖 Telegram Bot Setup

1. Message @BotFather on Telegram
2. Create new bot with `/newbot`
3. Get bot token
4. Get your chat ID by messaging your bot and visiting:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

## 📧 Email Setup

For Gmail, use App Passwords:
1. Enable 2FA on your Google account
2. Generate App Password for "Mail"
3. Use App Password in EMAIL_PASSWORD


### AI Model Configuration

Modify `GROQ_MODEL` in config.py to use different models:
- `moonshotai/kimi-k2-instruct` (recommended)
- `llama-3.1-70b-versatile`
- `mixtral-8x7b-32768`

### Notion Formatting

The system creates rich Notion pages with:
- Executive summary
- Key insights (bulleted)
- Market metrics with sentiment
- Outlook section
- Risk factors (highlighted)
- Action items (as to-do items)
- Full translated content (collapsible)

## 🐛 Troubleshooting

### Common Issues

1. **Scraping fails**: Check if site requires login credentials
2. **AI processing fails**: Verify Groq API key and model availability
3. **Notion creation fails**: Check database ID and integration permissions
4. **Telegram notifications fail**: Verify bot token and chat ID
5. **Email sending fails**: Use App Password, not regular password

### Logs

Check logs for detailed error information:
```bash
tail -f logs/market_report.log
```

### Error Notifications

The system sends error notifications via Telegram when processing fails.

## 🔒 Security

- Store all credentials in environment variables
- Use HTTPS for webhook endpoints
- Implement rate limiting in production
- Regularly rotate API keys
- Monitor logs for suspicious activity

## 📈 Monitoring

The system includes:
- Health check endpoint (`/api/health`)
- Comprehensive logging
- Error notifications via Telegram
- Quality scoring for content assessment

## 🚀 Production Deployment

For production use:
1. Set `DEBUG=False` in environment
2. Use proper WSGI server (gunicorn, uwsgi)
3. Implement rate limiting
4. Set up monitoring and alerting
5. Use environment-specific configurations
6. Implement database for persistence

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For issues and questions:
1. Check the troubleshooting guide
2. Review logs for error details
3. Test individual components using test endpoints
4. Open GitHub issue with detailed information

---