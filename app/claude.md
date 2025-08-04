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
```
## 11. Environment Configuration (.env)

```bash
# Pro Trading Skills
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
```
## 13. Test Files (tests/test_scraper.py)

```python
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.scraper import scrape_report_wrapper

report_url = "https://protradingskills.com/analysis/instrucciones-antes-de-la-conferencia-de-la-fed-importante-ver-ya/"

load_dotenv()

def test_scraper():
    print("🔍 Running scraper test...")
    try:
        report = scrape_report_wrapper(report_url)
        print(report)
    except Exception as e:
        print("❌ Scraper test failed with error:", e)

if __name__ == "__main__":
    test_scraper()
```

## 14. Integration Tests (tests/test_integrations.py)

```python
import os
import sys
from dotenv import load_dotenv
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.scraper import scrape_report_wrapper
from app.ai import GroqAIProcessor
from app.notion_client import NotionClient
from app.extractor import ContentExtractor
from app.notifier import TelegramNotifier
from app.notifier import EmailNotifier

ai_processor = GroqAIProcessor()
notion_client = NotionClient()
content_extractor = ContentExtractor()
telegram_notifier = TelegramNotifier()
email_notifier = EmailNotifier()

report_url = "https://protradingskills.com/analysis/instrucciones-antes-de-la-conferencia-de-la-fed-importante-ver-ya/"

load_dotenv()

def test_report_ai():
    print("🔍 Running Integration test...")
    report = scrape_report_wrapper(report_url)

    ai_analysis = ai_processor.translate_and_analyze(report["text_content"])
    full_response = content_extractor.create_summary_structure(report, ai_analysis)

    # Save to Notion
    notion_result = notion_client.create_report_page(full_response, report_url)
    notion_url = notion_result.get('page_url') if notion_result['success'] else None

    #  # Send Telegram notification
    telegram_success = telegram_notifier.send_notification(full_response, notion_url)
    print(telegram_success)
    # Send email
    email_success = email_notifier.send_report_email(full_response, report_url)
    print(email_success)

    
if __name__ == "__main__":
    test_report_ai()

```
## 15. PythonAnywhere WSGI Configuration (wsgi.py)


```python
#!/usr/bin/python3.13
import sys
import os

# IMPORTANT: Replace 'yourusername' with your actual username
username = 'username' 
project_name = 'market_report_ai'

# Add your project directory to Python path
path = f'/home/{username}/{project_name}'
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variables
os.environ['FLASK_APP'] = 'run.py'
os.environ['PYTHONPATH'] = path

# Python 3.13 specific optimizations
# Enable the new JIT compiler if available
os.environ.setdefault('PYTHONUNBUFFERED', '1')

# Import your Flask application
from app import create_app
application = create_app()

# For debugging (remove in production)
if __name__ == "__main__":
    application.run()
```
## 16. Deployment Script (deploy.sh)

```bash
#!/bin/bash

# Market Report AI Deployment Script for PythonAnywhere

echo "🚀 Starting deployment of Market Report AI..."

# Update system packages
echo "📦 Installing system dependencies..."
pip3 install --user -r requirements.txt

# Install Playwright browsers
echo "🎭 Installing Playwright browsers..."
python3 -m playwright install chromium

# If you get permission issues, try:
# python3 -m playwright install --with-deps chromium

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
```
## 17. Comprehensive README.md

```markdown



```

## 18. Environment Template (.env.example)

```bash
# Pro Trading Skills
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
```
## 9. Main Application Runner (run.py)

```python
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
```
## 10. Requirements File (requirements.txt)

```
Flask==3.0.3
python-dotenv
```
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
    # Pro Trading Skills
    PRO_USERNAME = os.getenv('PRO_USERNAME')
    PRO_PASSWORD = os.getenv('PRO_PASSWORD')

    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY')
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
    
    def translate_and_analyze(self, content: str) -> Dict[str, Any]:
        """
        Translate content to English and perform comprehensive analysis
        """
        print(content)

        try:
            prompt = self._create_analysis_prompt(content[:8000]) # the Limit of 8000 is to do not over pass the tokens limit

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
                temperature=0.6,
                max_completion_tokens=4096,
                top_p=1,
                stream=False,
                response_format={"type": "json_object"},
                stop=None,
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info("Successfully processed content with Groq AI")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return self._fallback_analysis(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Groq AI processing failed: {e}")
            return self._fallback_analysis(response.choices[0].message.content)
    
    def _fallback_analysis(self, content: str) -> Dict[str, Any]:
        """Fallback analysis when AI processing fails"""
        return {
            "translated_content": content,
            "summary": "Market report analysis temporarily unavailable. Please review original content.",
            "key_insights": ["AI analysis temporarily unavailable"],
            "market_metrics": {
                "mentioned_stocks": [],
                "sectors": [],
                "market_sentiment": "null"
            },
            "outlook": "Please review original report for outlook",
            "risk_factors": ["Manual review required"],
            "action_items": ["Review original report manually"],
            "confidence_level": ["Not Available"]
        }
    
        
    def _create_analysis_prompt(self, content: str) -> str:
        """Create a comprehensive analysis prompt for the AI"""
        return f"""
Analyze this financial market report and provide a comprehensive analysis in JSON format.

Please provide:
1. **Language Detection**: Identify the original language
2. **Translation**: If not in English, translate to English preserving all financial terms and numbers
3. **Content Analysis**: Extract and analyze the key information

Ensure the translation maintains financial terminology accuracy and the analysis focuses on actionable market intelligence.

Response format (must be valid JSON):

{{
    "translated_content": "Full content translated to English",
    "summary": "Comprehensive 3-4 paragraph summary highlighting the most critical insights",
    "key_insights": [
        "List of 5-7 most important insights from the report",
        "Each insight should be actionable and specific"
    ],
    "market_metrics": {{
        "mentioned_stocks": ["List of stocks/companies mentioned"],
        "sectors": ["List of sectors discussed"],
        "market_sentiment": "positive/negative/neutral"
    }},
    "outlook": "Brief outlook or predictions mentioned",
    "risk_factors": ["List of risks or concerns mentioned"],
    "action_items":  [
        "Specific, actionable recommendations for investors/traders",
        "Each recommendation should be concrete and implementable"
    ],
    "confidence_level": "High/Medium/Low - based on data quality and analysis certainty"
}}

Content to analyze:
{content}
"""
    
```

## 3. Web Scraping with Playwright (app/scraper.py)

```python
import asyncio
import logging
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page
from typing import Optional, Dict, Any, List
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
        self.page = await self.browser.new_page(user_agent=Config.USER_AGENT)
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def scrape_report(self, url: str) -> Dict[str, Any]:
        """
        Scrape market report from secure website
        """
        try:
            logger.info(f"Starting scrape for URL: {url}")
            
            # Navigate to the URL
            response = await self.page.goto("https://protradingskills.com/wp-login.php", wait_until="networkidle", timeout=60000)
            
            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")
            
            # Check if login is required
            if await self._needs_login():
                await self._handle_login()
            
            # Wait for content to load
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # Additional wait for dynamic content
            
            # Extract content
            content = await self._extract_content(url)
            
            logger.info("Successfully scraped report content")
            return {
                "success": True,
                "url": url,
                "title": content.get("title"),
                "html_content": content.get("html"),
                "text_content": content.get("text"),
                "report_images": content.get("images")
            }
            
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "html_content": "",
                "text_content": "",
                "report_images": []
            }
    
    async def _needs_login(self) -> bool:
        """Check if the page requires login"""
        login_input = await self.page.query_selector('input[id="user_login"]')
        return login_input is not None

    async def _handle_login(self):
        """Handle login process with multiple fallback strategies"""
        username = Config.PRO_USERNAME
        password = Config.PRO_PASSWORD
        
        if not username or not password:
            raise Exception("Username and password required for login")
        
        await self.page.fill('input[id="user_login"]', username)
        await self.page.fill('input[id="user_pass"]', password)
        await self.page.click('input[id="wp-submit"]')
                   
        # Wait for navigation after login
        await self.page.wait_for_load_state('networkidle', timeout=60000)
        return True
    
    async def _extract_content(self, report_url) -> Dict[str, Any]:
        """Extract content from the page"""
        try:
            # Go to the report page
            await self.page.goto(report_url, wait_until="networkidle", timeout=100000)

            # Get page title
            await self.page.locator("article h2").wait_for(state='visible', timeout=100000)
            title = await self.page.locator("article h2").text_content()
            
            # Content extraction strategies
            content_element = self.page.locator("div.entry-content")
            
            html_content = await content_element.inner_html()
            html_content = self._clean_scripts(html_content)
            text_content = await content_element.inner_text()
            images = self._get_images(html_content)

            return {
                "title": title,
                "html": html_content,
                "text": text_content,
                "images": images
            }
            
        except Exception as e:
            logger.error(f"Content extraction failed: {e}")
            return {
                "title": "Extraction Failed",
                "html": "",
                "text": "",
                "images": []
            }
        
    def _get_images(self, html_report) -> List[str]:
        soup = BeautifulSoup(html_report, "html.parser")

        # Extract external image URLs
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                images.append(src)

        return images
    
    def _clean_scripts(self, html): 
        # Parse the HTML
        soup = BeautifulSoup(html, 'html.parser')

        # Remove all <script> tags and their contents
        for script in soup.find_all('script'):
            script.decompose()

        # Cleaned HTML
        return str(soup)

def scrape_report_wrapper(url: str) -> Dict[str, Any]:
    """Synchronous wrapper for async scraping"""
    async def _scrape():
        async with WebScraper() as scraper:
            return await scraper.scrape_report(url)
    
    return asyncio.run(_scrape())

```

## 4. Content Extraction (app/extractor.py)

```python
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import List, Dict, Any
from datetime import datetime


logger = logging.getLogger(__name__)

class ContentExtractor:
    def extract_urls_from_email(self, email_content: str) -> List[str]:
        """Extract URLs from email HTML content that match specific domain and path"""
        soup = BeautifulSoup(email_content, "html.parser")
        urls = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            parsed = urlparse(href)

            # Only allow links from protradingskills.com with path starting with /analysis
            if parsed.netloc.lower() == "protradingskills.com" and parsed.path.startswith("/analysis"):
                urls.append(href)

        logger.info(f"Extracted urls: {len(urls)}")
        return urls
    

    def create_summary_structure(self, scraped_report: str, ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create a structured summary combining extracted content and AI analysis"""
        cleaned_content = self.clean_html_content(scraped_report)
        
        return {
            'metadata': {
                'title': cleaned_content['title'],
                'word_count': cleaned_content['word_count'],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  
            },
            'content': {
                'original_text': cleaned_content['main_content'],
                'translated_content': ai_analysis.get('translated_content', ''),
                'original_html': scraped_report.get('html_content', ''),
                'report_images': scraped_report.get('report_images')
            },
            'analysis': {
                'summary': ai_analysis.get('summary', ''),
                'key_insights': ai_analysis.get('key_insights', []),
                'market_metrics': ai_analysis.get('market_metrics', {}),
                'outlook': ai_analysis.get('outlook', ''),
                'risk_factors': ai_analysis.get('risk_factors', []),
                'action_items': ai_analysis.get('action_items', []),
                'confidence_level': ai_analysis.get('confidence_level', '')
            }
        }
    
    def clean_html_content(self, report: dict) -> dict:
        """Clean HTML content and prepare structured data from the scraped report"""

        title = report.get("title") or ""
        html_content = report.get("html_content") or ""
        
        # Strip HTML tags
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        return {
            "title": title.strip(),
            "main_content": text,
            "word_count": len(text.split())
        }
```

## 5. Notion Integration (app/notion_client.py)

```python
import logging
import html2text
from datetime import datetime
from typing import Dict, List, Any
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
    
    def create_report_page(self, analysis: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """Create a new page in Notion database for the market report"""
        try:
            # Prepare the page properties
            properties = self._build_page_properties(analysis, source_url)
            
            # Prepare the page content (blocks)
            children = self._build_page_content(analysis)
            
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
    
    def _build_page_properties(self, full_data: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """Build the properties for the Notion page"""

        metadata = full_data.get('metadata', {})
        analysis = full_data.get('analysis', {})
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
            "Confidence Level": {
                "select": {
                    "name": analysis.get('confidence_level')
                }
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
        content = report_data.get('content', {})
        
        try:
            # Summary section
            if analysis.get('summary'):
                blocks.extend([
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "📊 Summary"}}]
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
                                {"type": "text", "text": {"content": "**Mentioned Stocks:** "}, "annotations": {"bold": True}},
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
                                {"type": "text", "text": {"content": "**Sectors:** "}, "annotations": {"bold": True}},
                                {"type": "text", "text": {"content": ", ".join(metrics['sectors'])}}
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
            
            # Images
            if content.get("report_images"):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "📷 Gallery"}
                            }
                        ]
                    }
                })

                for img_url in content.get("report_images"):
                    if img_url.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                        # Use image block for direct image URLs
                        blocks.append({
                            "object": "block",
                            "type": "image",
                            "image": {
                                "type": "external",
                                "external": {
                                    "url": img_url
                                }
                            }
                        })
                    else:
                        # Use bookmark block for non-direct image URLs (like TradingView)
                        blocks.append({
                            "object": "block",
                            "type": "bookmark",
                            "bookmark": {
                                "url": img_url
                            }
                        })
            
            # # Full Translated Content (collapsible)
            # if content.get('translated_content'):
            #     blocks.extend([
            #         {
            #             "object": "block",
            #             "type": "heading_2",
            #             "heading_2": {
            #                 "rich_text": [{"type": "text", "text": {"content": "📄 Full Report (Translated)"}}]
            #             }
            #         },
            #         {
            #             "object": "block",
            #             "type": "toggle",
            #             "toggle": {
            #                 "rich_text": [{"type": "text", "text": {"content": "Click to expand full content"}}],
            #                 "children": [
            #                     {
            #                         "object": "block",
            #                         "type": "paragraph",
            #                         "paragraph": {
            #                             "rich_text": [{"type": "text", "text": {"content": content['translated_content'][:2000]}}]
            #                         }
            #                     }
            #                 ]
            #             }
            #         }
            #     ])
        
            # Original Report
            # Convert HTML to plain text with markdown formatting preserved
            html_converter = html2text.HTML2Text()
            html_converter.ignore_links = False  # Keep links if present
            html_converter.body_width = 0  # Prevent word wrapping
            if content.get('original_html'):
                blocks.extend([
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "📄 Original Report"}}]
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
                                        "rich_text": [{"type": "text", "text": {"content": html_converter.handle(content.get("original_html", "")[:2000])}}]
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

```
## 6. Notifications (app/notifier.py)

```python
import logging
import datetime
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
            
            message += f"⏰ {metadata.get('timestamp', 'Just now')}"
            
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
            msg['Subject'] = f"Pro-Trading Skills Report: {metadata.get('title', 'New Report')}"
            msg['From'] = self.email_address
            msg['To'] = self.recipient_email
            
            # Create HTML content
            html_content = self._create_html_email(report_data, source_url)
            
            # Create plain text content
            # text_content = self._create_text_email(report_data, source_url)
            
            # Attach content
            # msg.attach(MIMEText(text_content, 'plain'))
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
                <p><strong>Processed:</strong> {metadata.get('timestamp', 'Just now')}</p>
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

        # Original Content
        if content.get('original_html'):
            original_html = content.get('original_html')
            html += f"""
            <div class="section">
                <h2>📄 Original Report </h2>
                <div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; background-color: #f9f9f9;">
                    {original_html}
                </div>
            </div>
            """
        
        # Full Content (truncated)
        if content.get('translated_content'):
            translated = content['translated_content']
            html += f"""
            <div class="section">
                <h2>📄 Full Report (Translated)</h2>
                <div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; background-color: #f9f9f9;">
                    <p>{translated.replace('\n', '<br>')}</p>
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
        text += f"Processed: {metadata.get('timestamp', 'Just now')}\n\n"
        
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

```

## 7. Flask Routes (app/routes.py)

```python
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from .scraper import scrape_report_wrapper
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
        
        # Scrape the report
        scrape_report = scrape_report_wrapper(target_url)
        
        if not scrape_report['success']:
            error_msg = f"Failed to scrape report: {scrape_report.get('error', 'Unknown error')}"
            logger.error(error_msg)
            telegram_notifier.send_error_notification(error_msg, target_url)
            return jsonify({'error': error_msg}), 500
        
        # Process content with AI
        content_text = scrape_report['text_content']
        if not content_text.strip():
            content_text = scrape_report['html_content']
        
        ai_analysis = ai_processor.translate_and_analyze(content_text)
        full_response = extractor.create_summary_structure(scrape_report, ai_analysis)
        
        # Save to Notion
        notion_result = notion_client.create_report_page(full_response, target_url)
        notion_url = notion_result.get('page_url') if notion_result['success'] else None
        
        # Send Telegram notification
        telegram_success = telegram_notifier.send_notification(full_response, notion_url)
        
        # Send email
        email_success = email_notifier.send_report_email(full_response, target_url)
        
        # Prepare response
        response = {
            'success': True,
            'report_title': scrape_report['title'],
            'source_url': target_url,
            # 'word_count': ai_analysis['metadata']['word_count'],
            # 'quality_score': report_data['metadata']['quality_score'],
            'notion_success': notion_result['success'],
            'telegram_success': telegram_success,
            'email_success': email_success,
            'processed_at': ai_analysis['metadata']['timestamp']
        }
        
        if notion_url:
            response['notion_url'] = notion_url
        
        logger.info(f"Successfully processed report: {scrape_report['title']}")
        return jsonify(response)
        
    except Exception as e:
        error_msg = f"Unexpected error processing report: {str(e)}"
        logger.error(error_msg, exc_info=True)
        telegram_notifier.send_error_notification(error_msg)
        return jsonify({'error': error_msg}), 500
```