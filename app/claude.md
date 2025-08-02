```
Flask==2.3.3
python-dotenv==1.0.0
groq==0.4.1
requests==2.31.0
beautifulsoup4==4.12.2
playwright==1.40.0
lxml==4.9.3
python-telegram-bot==20.7
Werkzeug==2.3.7

## 11. Environment Configuration (.env)

```bash
# Flask Configuration
SECRET_KEY=your-super-secret-key-here
DEBUG=False
LOG_LEVEL=INFO

# Groq AI Configuration
GROQ_API_KEY=your-groq-api-key-here

# Notion Configuration
NOTION_API_KEY=your-notion-integration-token
NOTION_DATABASE_ID=your-notion-database-id

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
RECIPIENT_EMAIL=your-recipient@gmail.com

## 12. Git Ignore File (.gitignore)

```
# Environment variables
.env
.env.local
.env.production

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Flask
instance/
.webassets-cache

# Logs
*.log
logs/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Playwright browsers
/ms-playwright/

## 13. Test Files (tests/test_scraper.py)

```python
import unittest
from unittest.mock import patch, AsyncMock
import asyncio
from app.scraper import WebScraper, scrape_url

class TestWebScraper(unittest.TestCase):
    
    def test_scrape_url_basic(self):
        """Test basic URL scraping functionality"""
        # This is a basic test structure - you'll need to mock Playwright
        # for actual testing without running a real browser
        test_url = "https://httpbin.org/html"
        
        # In a real test, you'd mock the Playwright components
        # For now, this is the structure
        with patch('app.scraper.async_playwright') as mock_playwright:
            mock_context = AsyncMock()
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright.return_value.start = AsyncMock(return_value=mock_context)
            mock_context.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            
            # Mock page responses
            mock_page.goto = AsyncMock(return_value=AsyncMock(ok=True, status=200))
            mock_page.title = AsyncMock(return_value="Test Page")
            mock_page.inner_html = AsyncMock(return_value="<div>Test content</div>")
            mock_page.inner_text = AsyncMock(return_value="Test content")
            mock_page.query_selector_all = AsyncMock(return_value=[])
            
            # This test structure is ready for implementation
            pass
    
    def test_extract_urls_from_email(self):
        """Test URL extraction from email content"""
        from app.extractor import ContentExtractor
        
        extractor = ContentExtractor()
        
        email_content = """
        Check out this market report:
        https://example.com/market-report-2024
        
        Also see: https://finance.example.com/analysis
        
        Tracking link (should be filtered): https://bit.ly/track123
        """
        
        urls = extractor.extract_urls_from_email(email_content)
        
        self.assertIn("https://example.com/market-report-2024", urls)
        self.assertIn("https://finance.example.com/analysis", urls)
        # Tracking links should be filtered out
        self.assertNotIn("https://bit.ly/track123", urls)

if __name__ == '__main__':
    unittest.main()

## 14. Integration Tests (tests/test_integrations.py)

```python
import unittest
from unittest.mock import patch, MagicMock
import json
from app import create_app
from app.ai import GroqAIProcessor
from app.extractor import ContentExtractor

class TestIntegrations(unittest.TestCase):
    
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)
    
    @patch('app.ai.Groq')
    def test_ai_processing(self, mock_groq):
        """Test AI processing functionality"""
        # Mock Groq response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "translated_content": "Test translated content",
            "summary": "Test summary",
            "key_insights": ["Insight 1", "Insight 2"],
            "market_metrics": {
                "mentioned_stocks": ["AAPL"],
                "sectors": ["Technology"],
                "market_sentiment": "positive"
            },
            "outlook": "Positive outlook",
            "risk_factors": ["Risk 1"],
            "action_items": ["Action 1"]
        })
        
        mock_groq_instance = MagicMock()
        mock_groq_instance.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_groq_instance
        
        processor = GroqAIProcessor()
        result = processor.translate_and_analyze("Test content")
        
        self.assertIn('translated_content', result)
        self.assertIn('summary', result)
        self.assertIn('key_insights', result)
    
    def test_content_extraction(self):
        """Test content extraction functionality"""
        extractor = ContentExtractor()
        
        sample_html = """
        <html>
        <head><title>Market Report 2024</title></head>
        <body>
            <h1>Market Analysis</h1>
            <p>The market showed strong performance this quarter.</p>
            <h2>Key Metrics</h2>
            <p>Revenue increased by 15% to $2.5 billion.</p>
            <ul>
                <li>Technology sector up 12%</li>
                <li>Healthcare sector up 8%</li>
            </ul>
        </body>
        </html>
        """
        
        result = extractor.clean_html_content(sample_html)
        
        self.assertEqual(result['title'], 'Market Analysis')
        self.assertIn('market', result['main_content'].lower())
        self.assertTrue(len(result['headings']) > 0)
        self.assertTrue(len(result['paragraphs']) > 0)

if __name__ == '__main__':
    unittest.main()

## 15. PythonAnywhere WSGI Configuration (wsgi.py)

```python
#!/usr/bin/python3.10
import sys
import os

# Add your project directory to the sys.path
path = '/home/yourusername/market_report_ai'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ['PYTHONPATH'] = path

from app import create_app
application = create_app()

## 16. Deployment Script (deploy.sh)

```bash
#!/bin/bash

# Market Report AI Deployment Script for PythonAnywhere

echo "🚀 Starting deployment of Market Report AI..."

# Update system packages
echo "📦 Installing system dependencies..."
pip3.10 install --user -r requirements.txt

# Install Playwright browsers
echo "🎭 Installing Playwright browsers..."
python3.10 -m playwright install chromium

# Set up environment
echo "🔧 Setting up environment..."
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating template..."
    cp .env.example .env
    echo "Please edit .env file with your actual credentials"
fi

# Create logs directory
mkdir -p logs

# Set permissions
chmod +x run.py

echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Configure WSGI in PythonAnywhere web tab"
echo "3. Set source code path to: /home/yourusername/market_report_ai"
echo "4. Set WSGI configuration file to: /home/yourusername/market_report_ai/wsgi.py"
echo "5. Test endpoints using /api/health"
echo ""
echo "🔗 Test endpoints:"
echo "- Health check: https://yourusername.pythonanywhere.com/api/health"
echo "- Process report: https://yourusername.pythonanywhere.com/api/webhook/process-report"

## 17. Comprehensive README.md

```markdown
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
# Groq AI
GROQ_API_KEY=your-groq-api-key

# Notion
NOTION_API_KEY=secret_your-notion-integration-token
NOTION_DATABASE_ID=your-database-id

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# Email
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient@gmail.com
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
       "from": "{{from}}",
       "login_credentials": {
           "username": "optional-login-username",
           "password": "optional-login-password"
       }
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

## 🔧 Advanced Configuration

### Custom Login Handling

The scraper supports multiple login strategies. Add credentials to webhook payload:

```json
{
    "login_credentials": {
        "username": "your-username",
        "password": "your-password"
    }
}
```

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

**Built with ❤️ for automated market intelligence**
```

## 18. Environment Template (.env.example)

```bash
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

## 8. Flask Application Setup (app/__init__.py)

```python
import logging
from flask import Flask
from .config import Config
from .routes import api

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Register blueprints
    app.register_blueprint(api, url_prefix='/api')
    
    return app

## 9. Main Application Runner (run.py)

```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

## 10. Requirements File (requirements.txt)

```
Flask==2.3.3
python-dotenv# Market Report AI Automation System

## Project Structure
```
market_report_ai/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── routes.py
│   ├── ai.py
│   ├── extractor.py
│   ├── notifier.py
│   ├── scraper.py
│   └── notion_client.py
├── tests/
│   ├── test_scraper.py
│   └── test_integrations.py
├── run.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

## 1. Configuration Management (app/config.py)

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Groq AI settings
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_MODEL = "moonshotai/kimi-k2-instruct"
    
    # Notion settings
    NOTION_API_KEY = os.getenv('NOTION_API_KEY')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    
    # Telegram settings
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Email settings
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
    
    # Scraping settings
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
```

## 2. AI Processing with Groq (app/ai.py)

```python
import json
import logging
from groq import Groq
from typing import Dict, Any, Optional
from .config import Config

logger = logging.getLogger(__name__)

class GroqAIProcessor:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.model = Config.GROQ_MODEL
    
    def translate_and_analyze(self, content: str, source_language: str = "auto") -> Dict[str, Any]:
        """
        Translate content to English and perform comprehensive analysis
        """
        try:
            prompt = f"""
            You are a financial market analyst. Please analyze the following market report content and provide a comprehensive response in JSON format.

            Content to analyze:
            {content[:8000]}  # Limit content to avoid token limits

            Please provide your response in the following JSON structure:
            {{
                "translated_content": "Full content translated to English",
                "summary": "Concise 2-3 sentence summary of key points",
                "key_insights": [
                    "List of 3-5 key insights from the report"
                ],
                "market_metrics": {{
                    "mentioned_stocks": ["List of stocks/companies mentioned"],
                    "sectors": ["List of sectors discussed"],
                    "market_sentiment": "positive/negative/neutral"
                }},
                "outlook": "Brief outlook or predictions mentioned",
                "risk_factors": ["List of risks or concerns mentioned"],
                "action_items": ["List of actionable insights or recommendations"]
            }}

            Ensure the translation maintains financial terminology accuracy and the analysis focuses on actionable market intelligence.
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst with deep knowledge of global markets, trading, and investment strategies."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info("Successfully processed content with Groq AI")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return self._fallback_analysis(content)
        except Exception as e:
            logger.error(f"Groq AI processing failed: {e}")
            return self._fallback_analysis(content)
    
    def _fallback_analysis(self, content: str) -> Dict[str, Any]:
        """Fallback analysis when AI processing fails"""
        return {
            "translated_content": content[:2000] + "..." if len(content) > 2000 else content,
            "summary": "Market report analysis temporarily unavailable. Please review original content.",
            "key_insights": ["AI analysis temporarily unavailable"],
            "market_metrics": {
                "mentioned_stocks": [],
                "sectors": [],
                "market_sentiment": "neutral"
            },
            "outlook": "Please review original report for outlook",
            "risk_factors": ["Manual review required"],
            "action_items": ["Review original report manually"]
        }

    def quick_translate(self, text: str, target_language: str = "English") -> str:
        """Quick translation for shorter texts"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": f"Translate the following text to {target_language}, maintaining financial terminology accuracy:\n\n{text}"
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Quick translation failed: {e}")
            return text
```

## 3. Web Scraping with Playwright (app/scraper.py)

```python
import asyncio
import logging
from playwright.async_api import async_playwright, Browser, Page
from typing import Optional, Dict, Any
from .config import Config

logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = await self.browser.new_page()
        
        # Set user agent and viewport
        await self.page.set_user_agent(Config.USER_AGENT)
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def scrape_report(self, url: str, login_credentials: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Scrape market report from secure website
        """
        try:
            logger.info(f"Starting scrape for URL: {url}")
            
            # Navigate to the URL
            response = await self.page.goto(url, wait_until="networkidle", timeout=30000)
            
            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")
            
            # Check if login is required
            if await self._needs_login():
                if not login_credentials:
                    raise Exception("Login required but no credentials provided")
                await self._handle_login(login_credentials)
            
            # Wait for content to load
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # Additional wait for dynamic content
            
            # Extract content
            content = await self._extract_content()
            
            logger.info("Successfully scraped report content")
            return {
                "success": True,
                "url": url,
                "title": content.get("title", "Market Report"),
                "html_content": content.get("html", ""),
                "text_content": content.get("text", ""),
                "metadata": content.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "html_content": "",
                "text_content": "",
                "metadata": {}
            }
    
    async def _needs_login(self) -> bool:
        """Check if the page requires login"""
        login_indicators = [
            'input[type="password"]',
            'input[name*="password"]',
            'form[action*="login"]',
            '.login-form',
            '#login',
            'button[type="submit"]:has-text("Login")',
            'button:has-text("Sign In")'
        ]
        
        for selector in login_indicators:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    logger.info(f"Login required - found: {selector}")
                    return True
            except:
                continue
        
        return False
    
    async def _handle_login(self, credentials: Dict[str, str]):
        """Handle login process with multiple fallback strategies"""
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        
        if not username or not password:
            raise Exception("Username and password required for login")
        
        # Multiple selector strategies for username
        username_selectors = [
            'input[name="username"]',
            'input[name="email"]',
            'input[name="user"]',
            'input[type="email"]',
            'input[id*="username"]',
            'input[id*="email"]',
            'input[placeholder*="username"]',
            'input[placeholder*="email"]'
        ]
        
        # Multiple selector strategies for password
        password_selectors = [
            'input[name="password"]',
            'input[type="password"]',
            'input[id*="password"]',
            'input[placeholder*="password"]'
        ]
        
        # Login button selectors
        login_button_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Login")',
            'button:has-text("Sign In")',
            'button:has-text("Log In")',
            '.login-button',
            '#login-button'
        ]
        
        try:
            # Fill username
            username_filled = False
            for selector in username_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.fill(username)
                        username_filled = True
                        logger.info(f"Username filled using selector: {selector}")
                        break
                except:
                    continue
            
            if not username_filled:
                raise Exception("Could not find username field")
            
            # Fill password
            password_filled = False
            for selector in password_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.fill(password)
                        password_filled = True
                        logger.info(f"Password filled using selector: {selector}")
                        break
                except:
                    continue
            
            if not password_filled:
                raise Exception("Could not find password field")
            
            # Click login button
            login_clicked = False
            for selector in login_button_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.click()
                        login_clicked = True
                        logger.info(f"Login button clicked using selector: {selector}")
                        break
                except:
                    continue
            
            if not login_clicked:
                # Try pressing Enter as fallback
                await self.page.keyboard.press('Enter')
                logger.info("Login attempted using Enter key")
            
            # Wait for navigation or error
            try:
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                logger.info("Login successful")
            except:
                # Check for error messages
                error_selectors = ['.error', '.alert-danger', '.login-error', '[class*="error"]']
                for selector in error_selectors:
                    try:
                        error_element = await self.page.query_selector(selector)
                        if error_element:
                            error_text = await error_element.inner_text()
                            raise Exception(f"Login failed: {error_text}")
                    except:
                        continue
                
                logger.warning("Login status unclear, proceeding...")
        
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise
    
    async def _extract_content(self) -> Dict[str, Any]:
        """Extract content from the page"""
        try:
            # Get page title
            title = await self.page.title()
            
            # Content extraction strategies
            content_selectors = [
                'main',
                '.content',
                '.report-content',
                '.main-content',
                'article',
                '.post-content',
                '#content',
                '.entry-content',
                'body'
            ]
            
            html_content = ""
            text_content = ""
            
            # Try different content selectors
            for selector in content_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        html_content = await element.inner_html()
                        text_content = await element.inner_text()
                        if text_content.strip():  # Only use if we got meaningful content
                            logger.info(f"Content extracted using selector: {selector}")
                            break
                except:
                    continue
            
            # Fallback to full page if no specific content found
            if not text_content.strip():
                html_content = await self.page.inner_html('body')
                text_content = await self.page.inner_text('body')
                logger.info("Using full page content as fallback")
            
            # Extract metadata
            metadata = {}
            try:
                # Extract meta tags
                meta_tags = await self.page.query_selector_all('meta')
                for meta in meta_tags:
                    name = await meta.get_attribute('name') or await meta.get_attribute('property')
                    content = await meta.get_attribute('content')
                    if name and content:
                        metadata[name] = content
            except:
                pass
            
            return {
                "title": title,
                "html": html_content,
                "text": text_content,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Content extraction failed: {e}")
            return {
                "title": "Extraction Failed",
                "html": "",
                "text": "",
                "metadata": {}
            }

def scrape_url(url: str, login_credentials: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Synchronous wrapper for async scraping"""
    async def _scrape():
        async with WebScraper() as scraper:
            return await scraper.scrape_report(url, login_credentials)
    
    return asyncio.run(_scrape())
```

## 4. Content Extraction (app/extractor.py)

```python
import re
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ContentExtractor:
    def __init__(self):
        self.unwanted_tags = [
            'script', 'style', 'nav', 'header', 'footer', 
            'aside', 'advertisement', 'ads', 'sidebar'
        ]
        self.unwanted_classes = [
            'ad', 'ads', 'advertisement', 'sidebar', 'nav',
            'header', 'footer', 'social', 'share', 'comment'
        ]
    
    def extract_urls_from_email(self, email_content: str) -> List[str]:
        """Extract URLs from email content"""
        # Pattern to match URLs
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
        urls = re.findall(url_pattern, email_content)
        
        # Filter for likely report URLs (avoid tracking links, etc.)
        filtered_urls = []
        for url in urls:
            parsed = urlparse(url)
            # Skip common tracking domains
            tracking_domains = ['google.com', 'facebook.com', 'twitter.com', 'linkedin.com', 'bit.ly', 'tinyurl.com']
            if not any(domain in parsed.netloc.lower() for domain in tracking_domains):
                filtered_urls.append(url)
        
        logger.info(f"Extracted {len(filtered_urls)} URLs from email")
        return filtered_urls
    
    def clean_html_content(self, html_content: str) -> Dict[str, Any]:
        """Clean and extract meaningful content from HTML"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted tags
            for tag_name in self.unwanted_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()
            
            # Remove elements with unwanted classes
            for class_name in self.unwanted_classes:
                for element in soup.find_all(class_=re.compile(class_name, re.I)):
                    element.decompose()
            
            # Extract title
            title = ""
            title_candidates = [
                soup.find('h1'),
                soup.find('title'),
                soup.find(class_=re.compile('title', re.I)),
                soup.find(id=re.compile('title', re.I))
            ]
            
            for candidate in title_candidates:
                if candidate and candidate.get_text().strip():
                    title = candidate.get_text().strip()
                    break
            
            # Extract main content
            main_content = ""
            content_candidates = [
                soup.find('main'),
                soup.find('article'),
                soup.find(class_=re.compile('content|main|article', re.I)),
                soup.find(id=re.compile('content|main|article', re.I)),
                soup.find('body')
            ]
            
            for candidate in content_candidates:
                if candidate:
                    main_content = candidate.get_text().strip()
                    if len(main_content) > 100:  # Ensure we have substantial content
                        break
            
            # Extract headings for structure
            headings = []
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = heading.get_text().strip()
                if text:
                    headings.append({
                        'level': int(heading.name[1]),
                        'text': text
                    })
            
            # Extract paragraphs
            paragraphs = []
            for p in soup.find_all('p'):
                text = p.get_text().strip()
                if text and len(text) > 20:  # Filter out very short paragraphs
                    paragraphs.append(text)
            
            # Extract lists
            lists = []
            for ul in soup.find_all(['ul', 'ol']):
                items = [li.get_text().strip() for li in ul.find_all('li')]
                if items:
                    lists.append(items)
            
            # Extract tables (for financial data)
            tables = []
            for table in soup.find_all('table'):
                rows = []
                for tr in table.find_all('tr'):
                    cells = [td.get_text().strip() for td in tr.find_all(['td', 'th'])]
                    if cells:
                        rows.append(cells)
                if rows:
                    tables.append(rows)
            
            # Calculate content quality score
            quality_score = self._calculate_content_quality(main_content, headings, paragraphs)
            
            return {
                'title': title,
                'main_content': main_content,
                'headings': headings,
                'paragraphs': paragraphs,
                'lists': lists,
                'tables': tables,
                'quality_score': quality_score,
                'word_count': len(main_content.split()),
                'char_count': len(main_content)
            }
            
        except Exception as e:
            logger.error(f"HTML cleaning failed: {e}")
            return {
                'title': 'Extraction Failed',
                'main_content': html_content[:1000] if html_content else '',
                'headings': [],
                'paragraphs': [],
                'lists': [],
                'tables': [],
                'quality_score': 0,
                'word_count': 0,
                'char_count': 0
            }
    
    def _calculate_content_quality(self, content: str, headings: List[Dict], paragraphs: List[str]) -> float:
        """Calculate a quality score for the extracted content"""
        score = 0.0
        
        # Length score (0-40 points)
        word_count = len(content.split())
        if word_count > 500:
            score += 40
        elif word_count > 200:
            score += 30
        elif word_count > 100:
            score += 20
        elif word_count > 50:
            score += 10
        
        # Structure score (0-30 points)
        if headings:
            score += min(len(headings) * 5, 20)  # Up to 20 points for headings
        if paragraphs:
            score += min(len(paragraphs) * 2, 10)  # Up to 10 points for paragraphs
        
        # Financial content indicators (0-30 points)
        financial_keywords = [
            'market', 'stock', 'price', 'trading', 'investment', 'revenue',
            'profit', 'loss', 'earnings', 'financial', 'analysis', 'forecast',
            'economy', 'economic', 'growth', 'performance', 'sector', 'industry'
        ]
        
        content_lower = content.lower()
        keyword_matches = sum(1 for keyword in financial_keywords if keyword in content_lower)
        score += min(keyword_matches * 2, 30)
        
        return min(score, 100.0)  # Cap at 100
    
    def extract_key_metrics(self, content: str) -> Dict[str, Any]:
        """Extract key financial metrics from content"""
        metrics = {
            'currencies': [],
            'percentages': [],
            'numbers': [],
            'dates': [],
            'companies': [],
            'financial_terms': []
        }
        
        try:
            # Extract currencies
            currency_pattern = r'[\$€£¥₹]\s*[\d,]+\.?\d*[KMB]?'
            metrics['currencies'] = list(set(re.findall(currency_pattern, content)))
            
            # Extract percentages
            percentage_pattern = r'\d+\.?\d*\s*%'
            metrics['percentages'] = list(set(re.findall(percentage_pattern, content)))
            
            # Extract large numbers
            number_pattern = r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:million|billion|trillion|M|B|T)?\b'
            metrics['numbers'] = list(set(re.findall(number_pattern, content, re.I)))
            
            # Extract dates
            date_pattern = r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b'
            metrics['dates'] = list(set(re.findall(date_pattern, content, re.I)))
            
            # Extract potential company names (capitalized words)
            company_pattern = r'\b[A-Z][a-z]+ (?:Inc|Corp|Ltd|LLC|AG|SA|PLC|Co)\b'
            metrics['companies'] = list(set(re.findall(company_pattern, content)))
            
            # Financial terms
            financial_terms = [
                'revenue', 'profit', 'loss', 'earnings', 'EBITDA', 'ROI', 'ROE',
                'dividend', 'yield', 'volatility', 'beta', 'P/E', 'market cap',
                'IPO', 'merger', 'acquisition', 'bullish', 'bearish'
            ]
            
            content_lower = content.lower()
            found_terms = [term for term in financial_terms if term.lower() in content_lower]
            metrics['financial_terms'] = found_terms
            
        except Exception as e:
            logger.error(f"Metrics extraction failed: {e}")
        
        return metrics
    
    def create_summary_structure(self, content: str, ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create a structured summary combining extracted content and AI analysis"""
        cleaned_content = self.clean_html_content(content)
        metrics = self.extract_key_metrics(cleaned_content['main_content'])
        
        return {
            'metadata': {
                'title': cleaned_content['title'],
                'word_count': cleaned_content['word_count'],
                'quality_score': cleaned_content['quality_score'],
                'extraction_timestamp': None  # Will be set by the calling function
            },
            'content': {
                'original_text': cleaned_content['main_content'],
                'translated_content': ai_analysis.get('translated_content', ''),
                'structure': {
                    'headings': cleaned_content['headings'],
                    'paragraphs': len(cleaned_content['paragraphs']),
                    'tables': len(cleaned_content['tables']),
                    'lists': len(cleaned_content['lists'])
                }
            },
            'analysis': {
                'summary': ai_analysis.get('summary', ''),
                'key_insights': ai_analysis.get('key_insights', []),
                'market_metrics': ai_analysis.get('market_metrics', {}),
                'outlook': ai_analysis.get('outlook', ''),
                'risk_factors': ai_analysis.get('risk_factors', []),
                'action_items': ai_analysis.get('action_items', [])
            },
            'extracted_metrics': metrics
        }
```

## 5. Notion Integration (app/notion_client.py)

```python
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from .config import Config

logger = logging.getLogger(__name__)

class NotionClient:
    def __init__(self):
        self.api_key = Config.NOTION_API_KEY
        self.database_id = Config.NOTION_DATABASE_ID
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def create_report_page(self, report_data: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """Create a new page in Notion database for the market report"""
        try:
            # Prepare the page properties
            properties = self._build_page_properties(report_data, source_url)
            
            # Prepare the page content (blocks)
            children = self._build_page_content(report_data)
            
            # Create the page
            payload = {
                "parent": {"database_id": self.database_id},
                "properties": properties,
                "children": children
            }
            
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully created Notion page: {result['id']}")
                return {
                    "success": True,
                    "page_id": result['id'],
                    "page_url": result['url']
                }
            else:
                logger.error(f"Notion API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Failed to create Notion page: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_page_properties(self, report_data: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """Build the properties for the Notion page"""
        metadata = report_data.get('metadata', {})
        analysis = report_data.get('analysis', {})
        metrics = analysis.get('market_metrics', {})
        
        properties = {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": metadata.get('title', 'Market Report')[:100]  # Notion title limit
                        }
                    }
                ]
            },
            "Source URL": {
                "url": source_url
            },
            "Date": {
                "date": {
                    "start": datetime.now().isoformat()
                }
            },
            "Status": {
                "select": {
                    "name": "New"
                }
            },
            "Market Sentiment": {
                "select": {
                    "name": metrics.get('market_sentiment', 'neutral').title()
                }
            },
            "Word Count": {
                "number": metadata.get('word_count', 0)
            },
            "Quality Score": {
                "number": metadata.get('quality_score', 0)
            }
        }
        
        # Add sectors and stocks as multi-select if available
        if metrics.get('sectors'):
            properties["Sectors"] = {
                "multi_select": [
                    {"name": sector[:100]} for sector in metrics['sectors'][:10]  # Limit to 10 items
                ]
            }
        
        if metrics.get('mentioned_stocks'):
            properties["Stocks"] = {
                "multi_select": [
                    {"name": stock[:100]} for stock in metrics['mentioned_stocks'][:10]
                ]
            }
        
        return properties
    
    def _build_page_content(self, report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build the content blocks for the Notion page"""
        blocks = []
        analysis = report_data.get('analysis', {})
        
        try:
            # Summary section
            if analysis.get('summary'):
                blocks.extend([
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "📊 Executive Summary"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": analysis['summary']}}]
                        }
                    }
                ])
            
            # Key Insights
            if analysis.get('key_insights'):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "💡 Key Insights"}}]
                    }
                })
                
                for insight in analysis['key_insights']:
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": insight}}]
                        }
                    })
            
            # Market Metrics
            metrics = analysis.get('market_metrics', {})
            if any(metrics.values()):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "📈 Market Metrics"}}]
                    }
                })
                
                if metrics.get('mentioned_stocks'):
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": "**Mentioned Stocks:** ", "annotations": {"bold": True}}},
                                {"type": "text", "text": {"content": ", ".join(metrics['mentioned_stocks'][:10])}}
                            ]
                        }
                    })
                
                if metrics.get('sectors'):
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": "**Sectors:** ", "annotations": {"bold": True}}},
                                {"type": "text", "text": {"content": ", ".join(metrics['sectors'][:10])}}
                            ]
                        }
                    })
            
            # Outlook
            if analysis.get('outlook'):
                blocks.extend([
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "🔮 Market Outlook"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": analysis['outlook']}}]
                        }
                    }
                ])
            
            # Risk Factors
            if analysis.get('risk_factors'):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "⚠️ Risk Factors"}}]
                    }
                })
                
                for risk in analysis['risk_factors']:
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": risk}}]
                        }
                    })
            
            # Action Items
            if analysis.get('action_items'):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "✅ Action Items"}}]
                    }
                })
                
                for item in analysis['action_items']:
                    blocks.append({
                        "object": "block",
                        "type": "to_do",
                        "to_do": {
                            "rich_text": [{"type": "text", "text": {"content": item}}],
                            "checked": False
                        }
                    })
            
            # Full Translated Content (collapsible)
            if report_data.get('content', {}).get('translated_content'):
                blocks.extend([
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "📄 Full Report (Translated)"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "toggle",
                        "toggle": {
                            "rich_text": [{"type": "text", "text": {"content": "Click to expand full content"}}],
                            "children": [
                                {
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [{"type": "text", "text": {"content": report_data['content']['translated_content'][:2000]}}]
                                    }
                                }
                            ]
                        }
                    }
                ])
        
        except Exception as e:
            logger.error(f"Error building Notion content blocks: {e}")
            # Fallback basic content
            blocks = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": "Report processed successfully. Error in detailed formatting."}}]
                    }
                }
            ]
        
        return blocks
    
    def update_page_status(self, page_id: str, status: str) -> bool:
        """Update the status of a Notion page"""
        try:
            payload = {
                "properties": {
                    "Status": {
                        "select": {
                            "name": status
                        }
                    }
                }
            }
            
            response = requests.patch(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers,
                json=payload,
                timeout=15
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to update Notion page status: {e}")
            return False

## 6. Telegram Notifications (app/notifier.py)

```python
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from .config import Config

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_notification(self, report_data: Dict[str, Any], notion_url: str = None) -> bool:
        """Send Telegram notification about new market report"""
        try:
            metadata = report_data.get('metadata', {})
            analysis = report_data.get('analysis', {})
            
            # Create message
            title = metadata.get('title', 'New Market Report')
            summary = analysis.get('summary', 'Report processed successfully')
            
            message = f"📊 **{title}**\n\n"
            message += f"📝 **Summary:**\n{summary}\n\n"
            
            # Add key insights
            if analysis.get('key_insights'):
                message += "💡 **Key Insights:**\n"
                for insight in analysis['key_insights'][:3]:  # Limit to 3 insights
                    message += f"• {insight}\n"
                message += "\n"
            
            # Add market sentiment
            metrics = analysis.get('market_metrics', {})
            if metrics.get('market_sentiment'):
                sentiment_emoji = {
                    'positive': '📈',
                    'negative': '📉',
                    'neutral': '➡️'
                }
                emoji = sentiment_emoji.get(metrics['market_sentiment'], '➡️')
                message += f"{emoji} **Sentiment:** {metrics['market_sentiment'].title()}\n\n"
            
            # Add Notion link
            if notion_url:
                message += f"🔗 [View in Notion]({notion_url})\n"
            
            message += f"⏰ {metadata.get('extraction_timestamp', 'Just now')}"
            
            # Send message
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    def send_error_notification(self, error_message: str, context: str = "") -> bool:
        """Send error notification via Telegram"""
        try:
            message = f"🚨 **Market Report Processing Error**\n\n"
            message += f"**Error:** {error_message}\n"
            if context:
                message += f"**Context:** {context}\n"
            message += f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=15
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
            return False

class EmailNotifier:
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.email_address = Config.EMAIL_ADDRESS
        self.email_password = Config.EMAIL_PASSWORD
        self.recipient_email = Config.RECIPIENT_EMAIL
    
    def send_report_email(self, report_data: Dict[str, Any], source_url: str) -> bool:
        """Send processed report via email"""
        try:
            metadata = report_data.get('metadata', {})
            analysis = report_data.get('analysis', {})
            content = report_data.get('content', {})
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Market Report: {metadata.get('title', 'New Report')}"
            msg['From'] = self.email_address
            msg['To'] = self.recipient_email
            
            # Create HTML content
            html_content = self._create_html_email(report_data, source_url)
            
            # Create plain text content
            text_content = self._create_text_email(report_data, source_url)
            
            # Attach content
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            logger.info("Email sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _create_html_email(self, report_data: Dict[str, Any], source_url: str) -> str:
        """Create HTML email content"""
        metadata = report_data.get('metadata', {})
        analysis = report_data.get('analysis', {})
        content = report_data.get('content', {})
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Market Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; }}
                .insights {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; }}
                .risks {{ background-color: #fff3cd; padding: 15px; border-radius: 5px; }}
                .action-items {{ background-color: #d4edda; padding: 15px; border-radius: 5px; }}
                ul {{ padding-left: 20px; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 {metadata.get('title', 'Market Report')}</h1>
                <p><strong>Source:</strong> <a href="{source_url}">{source_url}</a></p>
                <p><strong>Processed:</strong> {metadata.get('extraction_timestamp', 'Just now')}</p>
            </div>
            
            <div class="section">
                <h2>📝 Executive Summary</h2>
                <p>{analysis.get('summary', 'Summary not available')}</p>
            </div>
        """
        
        # Key Insights
        if analysis.get('key_insights'):
            html += """
            <div class="section insights">
                <h2>💡 Key Insights</h2>
                <ul>
            """
            for insight in analysis['key_insights']:
                html += f"<li>{insight}</li>"
            html += "</ul></div>"
        
        # Market Outlook
        if analysis.get('outlook'):
            html += f"""
            <div class="section">
                <h2>🔮 Market Outlook</h2>
                <p>{analysis['outlook']}</p>
            </div>
            """
        
        # Risk Factors
        if analysis.get('risk_factors'):
            html += """
            <div class="section risks">
                <h2>⚠️ Risk Factors</h2>
                <ul>
            """
            for risk in analysis['risk_factors']:
                html += f"<li>{risk}</li>"
            html += "</ul></div>"
        
        # Action Items
        if analysis.get('action_items'):
            html += """
            <div class="section action-items">
                <h2>✅ Action Items</h2>
                <ul>
            """
            for item in analysis['action_items']:
                html += f"<li>{item}</li>"
            html += "</ul></div>"
        
        # Full Content (truncated)
        if content.get('translated_content'):
            translated = content['translated_content']
            preview = translated[:1000] + "..." if len(translated) > 1000 else translated
            html += f"""
            <div class="section">
                <h2>📄 Full Report (Translated)</h2>
                <div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; background-color: #f9f9f9;">
                    <p>{preview.replace('\n', '<br>')}</p>
                </div>
            </div>
            """
        
        html += """
            <div class="footer">
                <p>This report was automatically processed by the Market Report AI system.</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_text_email(self, report_data: Dict[str, Any], source_url: str) -> str:
        """Create plain text email content"""
        metadata = report_data.get('metadata', {})
        analysis = report_data.get('analysis', {})
        
        text = f"MARKET REPORT: {metadata.get('title', 'New Report')}\n"
        text += "=" * 50 + "\n\n"
        text += f"Source: {source_url}\n"
        text += f"Processed: {metadata.get('extraction_timestamp', 'Just now')}\n\n"
        
        text += "EXECUTIVE SUMMARY\n"
        text += "-" * 20 + "\n"
        text += f"{analysis.get('summary', 'Summary not available')}\n\n"
        
        if analysis.get('key_insights'):
            text += "KEY INSIGHTS\n"
            text += "-" * 20 + "\n"
            for insight in analysis['key_insights']:
                text += f"• {insight}\n"
            text += "\n"
        
        if analysis.get('outlook'):
            text += "MARKET OUTLOOK\n"
            text += "-" * 20 + "\n"
            text += f"{analysis['outlook']}\n\n"
        
        if analysis.get('risk_factors'):
            text += "RISK FACTORS\n"
            text += "-" * 20 + "\n"
            for risk in analysis['risk_factors']:
                text += f"• {risk}\n"
            text += "\n"
        
        if analysis.get('action_items'):
            text += "ACTION ITEMS\n"
            text += "-" * 20 + "\n"
            for item in analysis['action_items']:
                text += f"• {item}\n"
            text += "\n"
        
        text += "\n" + "=" * 50 + "\n"
        text += "This report was automatically processed by the Market Report AI system."
        
        return text

## 7. Flask Routes (app/routes.py)

```python
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from .scraper import scrape_url
from .extractor import ContentExtractor
from .ai import GroqAIProcessor
from .notion_client import NotionClient
from .notifier import TelegramNotifier, EmailNotifier

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__)

# Initialize components
extractor = ContentExtractor()
ai_processor = GroqAIProcessor()
notion_client = NotionClient()
telegram_notifier = TelegramNotifier()
email_notifier = EmailNotifier()

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@api.route('/webhook/process-report', methods=['POST'])
def process_report():
    """Main webhook endpoint for processing market reports"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        logger.info(f"Received webhook data: {data.keys()}")
        
        # Extract email content and URLs
        email_html = data.get('email_html', '')
        email_text = data.get('email_text', '')
        subject = data.get('subject', 'Market Report')
        
        # Try to extract URLs from both HTML and plain text
        urls = []
        if email_html:
            urls.extend(extractor.extract_urls_from_email(email_html))
        if email_text and not urls:
            urls.extend(extractor.extract_urls_from_email(email_text))
        
        if not urls:
            error_msg = "No URLs found in email content"
            logger.error(error_msg)
            telegram_notifier.send_error_notification(error_msg, f"Subject: {subject}")
            return jsonify({'error': error_msg}), 400
        
        # Process the first URL found
        target_url = urls[0]
        logger.info(f"Processing URL: {target_url}")
        
        # Extract login credentials if provided
        login_credentials = data.get('login_credentials')
        
        # Scrape the report
        scrape_result = scrape_url(target_url, login_credentials)
        
        if not scrape_result['success']:
            error_msg = f"Failed to scrape report: {scrape_result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            telegram_notifier.send_error_notification(error_msg, target_url)
            return jsonify({'error': error_msg}), 500
        
        # Process content with AI
        content_text = scrape_result['text_content']
        if not content_text.strip():
            content_text = scrape_result['html_content']
        
        ai_analysis = ai_processor.translate_and_analyze(content_text)
        
        # Create structured report data
        report_data = extractor.create_summary_structure(
            scrape_result['html_content'], 
            ai_analysis
        )
        report_data['metadata']['extraction_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Save to Notion
        notion_result = notion_client.create_report_page(report_data, target_url)
        notion_url = notion_result.get('page_url') if notion_result['success'] else None
        
        # Send Telegram notification
        telegram_success = telegram_notifier.send_notification(report_data, notion_url)
        
        # Send email
        email_success = email_notifier.send_report_email(report_data, target_url)
        
        # Prepare response
        response = {
            'success': True,
            'report_title': report_data['metadata']['title'],
            'source_url': target_url,
            'word_count': report_data['metadata']['word_count'],
            'quality_score': report_data['metadata']['quality_score'],
            'notion_success': notion_result['success'],
            'telegram_success': telegram_success,
            'email_success': email_success,
            'processed_at': report_data['metadata']['extraction_timestamp']
        }
        
        if notion_url:
            response['notion_url'] = notion_url
        
        logger.info(f"Successfully processed report: {report_data['metadata']['title']}")
        return jsonify(response)
        
    except Exception as e:
        error_msg = f"Unexpected error processing report: {str(e)}"
        logger.error(error_msg, exc_info=True)
        telegram_notifier.send_error_notification(error_msg)
        return jsonify({'error': error_msg}), 500

@api.route('/test-scraper', methods=['POST'])
def test_scraper():
    """Test endpoint for scraping functionality"""
    try:
        data = request.get_json()
        url = data.get('url')
        login_credentials = data.get('login_credentials')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        result = scrape_url(url, login_credentials)
        
        # Return limited content to avoid large responses
        if result['success']:
            result['text_content'] = result['text_content'][:500] + "..." if len(result['text_content']) > 500 else result['text_content']
            result['html_content'] = "HTML content available (" + str(len(result['html_content'])) + " chars)"
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Test scraper error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/test-ai', methods=['POST'])
def test_ai():
    """Test endpoint for AI processing"""
    try:
        data = request.get_json()
        content = data.get('content')
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        result = ai_processor.translate_and_analyze(content)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Test AI error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/test-notion', methods=['POST'])
def test_notion():
    """Test endpoint for Notion integration"""
    try:
        # Create sample report data
        sample_data = {
            'metadata': {
                'title': 'Test Market Report',
                'word_count': 1500,
                'quality_score': 85.0,
                'extraction_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'analysis': {
                'summary': 'This is a test market report summary for testing Notion integration.',
                'key_insights': [
                    'Test insight number one',
                    'Test insight number two',
                    'Test insight number three'
                ],
                'market_metrics': {
                    'mentioned_stocks': ['AAPL', 'GOOGL', 'TSLA'],
                    'sectors': ['Technology', 'Automotive'],
                    'market_sentiment': 'positive'
                },
                'outlook': 'Positive outlook for testing purposes',
                'risk_factors': ['Test risk factor'],
                'action_items': ['Test this integration', 'Verify functionality']
            }
        }
        
        result = notion_client.create_report_page(sample_data, 'https://example.com/test')
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Test Notion error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/test-telegram', methods=['POST'])
def test_telegram():
    """Test endpoint for Telegram notifications"""
    try:
        sample_data = {
            'metadata': {
                'title': 'Test Market Report',
                'extraction_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'analysis': {
                'summary': 'This is a test notification from the Market Report AI system.',
                'key_insights': ['System is working correctly', 'Telegram integration active'],
                'market_metrics': {
                    'market_sentiment': 'positive'
                }
            }
        }
        
        success = telegram_notifier.send_notification(sample_data, 'https://notion.so/test')
        return jsonify({'success': success})
        
    except Exception as e:
        logger.error(f"Test Telegram error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/test-email', methods=['POST'])
def test_email():
    """Test endpoint for email notifications"""
    try:
        sample_data = {
            'metadata': {
                'title': 'Test Market Report',
                'extraction_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'analysis': {
                'summary': 'This is a test email from the Market Report AI system.',
                'key_insights': ['Email system working correctly', 'Integration successful'],
                'outlook': 'System operational',
                'risk_factors': ['No risks detected in test'],
                'action_items': ['Verify email receipt', 'Confirm formatting']
            },
            'content': {
                'translated_content': 'This is the full translated content of the test report. It demonstrates how the email will look when a real report is processed.'
            }
        }
        
        success = email_notifier.send_report_email(sample_data, 'https://example.com/test')
        return jsonify({'success': success})
        
    except Exception as e:
        logger.error(f"Test email error: {e}")
        return jsonify({'error': str(e)}), 500
Improve
Explain
Claude