from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from notion_client import Client
import telegram
import asyncio
from datetime import datetime
import os
import re
# import openai
# Alternative AI imports
# import anthropic
from groq import Groq

app = Flask(__name__)

# Configuration
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBSITE_USERNAME = os.getenv('WEBSITE_USERNAME')
WEBSITE_PASSWORD = os.getenv('WEBSITE_PASSWORD')

# AI Configuration (choose one)
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Initialize clients
notion = Client(auth=NOTION_TOKEN)
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# AI client setup (OpenAI example)
openai.api_key = OPENAI_API_KEY

# Alternative setups:
# anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
# groq_client = Groq(api_key=GROQ_API_KEY)

def extract_url_from_email(email_body):
    """Extract URL from email content"""
    # Try HTML body first
    soup = BeautifulSoup(email_body, 'html.parser')
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link['href']
        if any(keyword in href.lower() for keyword in ['report', 'market', 'analysis']):
            return href
    
    # Fallback to regex for plain text
    url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+|[^\s<>"\'.]+\.[a-z]{2,}[^\s<>"\'.]*'
    urls = re.findall(url_pattern, email_body, re.IGNORECASE)
    
    for url in urls:
        if any(keyword in url.lower() for keyword in ['report', 'market', 'analysis']):
            return url if url.startswith('http') else f'https://{url}'
    
    return urls[0] if urls else None

async def login_and_fetch_report(report_url):
    """Login to website and fetch report content using Playwright"""
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        )
        
        try:
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()
            
            # Navigate to the URL
            await page.goto(report_url, wait_until='networkidle')
            
            # Check if login is required
            login_selectors = [
                'input[name="username"]',
                'input[name="email"]',
                'input[type="email"]',
                'input[id*="username"]',
                'input[id*="email"]',
                '#username',
                '#email',
                '.username',
                '.email'
            ]
            
            login_found = False
            for selector in login_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    login_found = True
                    break
                except:
                    continue
            
            if login_found:
                print("Login form detected, attempting login...")
                
                # Find and fill username
                username_filled = False
                for selector in login_selectors:
                    try:
                        await page.fill(selector, WEBSITE_USERNAME)
                        username_filled = True
                        break
                    except:
                        continue
                
                # Find and fill password
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[id*="password"]',
                    '#password',
                    '.password'
                ]
                
                password_filled = False
                for selector in password_selectors:
                    try:
                        await page.fill(selector, WEBSITE_PASSWORD)
                        password_filled = True
                        break
                    except:
                        continue
                
                # Submit form
                if username_filled and password_filled:
                    submit_selectors = [
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:has-text("Login")',
                        'button:has-text("Sign in")',
                        '.login-button',
                        '.submit-button'
                    ]
                    
                    for selector in submit_selectors:
                        try:
                            await page.click(selector)
                            break
                        except:
                            continue
                    
                    # Wait for navigation after login
                    await page.wait_for_load_state('networkidle')
            
            # Get page content
            html_content = await page.content()
            return html_content
            
        finally:
            await browser.close()

def extract_main_content(html_content):
    """Extract main content from HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
        element.decompose()
    
    # Try to find main content areas (ordered by priority)
    content_selectors = [
        'main',
        'article',
        '.content',
        '.main-content',
        '.report-content',
        '.article-content',
        '#content',
        '#main',
        '.post-content',
        '.entry-content'
    ]
    
    main_content = None
    for selector in content_selectors:
        element = soup.select_one(selector)
        if element:
            main_content = element.get_text(separator=' ', strip=True)
            break
    
    if not main_content:
        # Fallback: get all paragraphs and divs with substantial text
        text_elements = soup.find_all(['p', 'div', 'span'])
        content_parts = []
        
        for element in text_elements:
            text = element.get_text(strip=True)
            if len(text) > 50:  # Only include substantial text
                content_parts.append(text)
        
        main_content = ' '.join(content_parts)
    
    # Clean up the content
    main_content = re.sub(r'\s+', ' ', main_content)  # Normalize whitespace
    main_content = re.sub(r'\n+', '\n', main_content)  # Normalize newlines
    
    return main_content.strip()

async def ai_translate_and_summarize(content, source_language="auto"):
    """Use AI to translate and summarize content"""
    
    # Prepare the prompt
    prompt = f"""
You are a financial analyst AI assistant. Please analyze the following market report content and provide:

1. **Translation**: If the content is not in English, translate it to English while preserving all financial terms, numbers, and technical analysis accurately.

2. **Summary**: Create a concise but comprehensive summary that includes:
   - Key market insights and trends
   - Important financial data and metrics
   - Market outlook and forecasts
   - Any actionable recommendations
   - Critical risk factors mentioned

Please format your response as JSON with these exact keys:
{{
    "original_language": "detected language or 'English'",
    "translated_content": "full translated content (or original if already English)",
    "summary": "comprehensive summary focusing on key financial insights",
    "key_metrics": "important numbers, percentages, and financial data mentioned",
    "market_outlook": "future predictions and market direction",
    "risk_factors": "any risks or concerns mentioned"
}}

Content to analyze:
{content[:8000]}  # Limit content length for API
"""

    try:
        # OpenAI GPT-4 example
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # or "gpt-4o" for better quality
            messages=[
                {"role": "system", "content": "You are an expert financial analyst and translator. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content
        
        # Parse JSON response
        import json
        try:
            result = json.loads(result_text)
            return result
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "original_language": "unknown",
                "translated_content": content,
                "summary": result_text,
                "key_metrics": "Unable to extract",
                "market_outlook": "Unable to extract",
                "risk_factors": "Unable to extract"
            }
        
    except Exception as e:
        print(f"AI processing error: {e}")
        return {
            "original_language": "unknown",
            "translated_content": content,
            "summary": content[:500] + "...",
            "key_metrics": "Error in processing",
            "market_outlook": "Error in processing", 
            "risk_factors": "Error in processing"
        }

# Alternative AI implementations:

async def ai_translate_anthropic(content):
    """Alternative using Anthropic Claude"""
    try:
        message = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            temperature=0.3,
            messages=[
                {"role": "user", "content": f"Translate and summarize this financial content to English: {content[:8000]}"}
            ]
        )
        return {"summary": message.content[0].text, "translated_content": content}
    except Exception as e:
        print(f"Anthropic error: {e}")
        return {"summary": content[:500], "translated_content": content}

async def ai_translate_groq(content):
    """Alternative using Groq (faster, cheaper)"""
    try:
        completion = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "user", "content": f"Translate to English and create a summary of this financial report: {content[:8000]}"}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        return {"summary": completion.choices[0].message.content, "translated_content": content}
    except Exception as e:
        print(f"Groq error: {e}")
        return {"summary": content[:500], "translated_content": content}

def save_to_notion(title, ai_result, report_url):
    """Save report to Notion database with AI-enhanced data"""
    try:
        properties = {
            "Title": {
                "title": [{"text": {"content": title}}]
            },
            "Summary": {
                "rich_text": [{"text": {"content": ai_result.get('summary', '')[:2000]}}]
            },
            "Report URL": {
                "url": report_url
            },
            "Date": {
                "date": {"start": datetime.now().isoformat()}
            },
            "Original Language": {
                "rich_text": [{"text": {"content": ai_result.get('original_language', 'Unknown')}}]
            },
            "Key Metrics": {
                "rich_text": [{"text": {"content": ai_result.get('key_metrics', '')[:2000]}}]
            },
            "Market Outlook": {
                "rich_text": [{"text": {"content": ai_result.get('market_outlook', '')[:2000]}}]
            },
            "Risk Factors": {
                "rich_text": [{"text": {"content": ai_result.get('risk_factors', '')[:2000]}}]
            },
            "Status": {
                "select": {"name": "New"}
            }
        }
        
        # Add full translated content as page content
        children = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Full Translated Content"}}]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": ai_result.get('translated_content', '')[:2000]}}]
                }
            }
        ]
        
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties,
            children=children
        )
        
        return True
    except Exception as e:
        print(f"Notion error: {e}")
        return False

async def send_telegram_notification(title, ai_result, report_url):
    """Send enhanced Telegram notification with AI insights"""
    try:
        message = f"""
🔔 **New Market Report Processed**

**{title}**

**🔍 Key Summary:**
{ai_result.get('summary', 'No summary available')[:400]}...

**📊 Key Metrics:**
{ai_result.get('key_metrics', 'No metrics extracted')[:200]}

**📈 Market Outlook:**
{ai_result.get('market_outlook', 'No outlook available')[:200]}

**⚠️ Risk Factors:**
{ai_result.get('risk_factors', 'No risks identified')[:200]}

**🌐 Original Language:** {ai_result.get('original_language', 'Unknown')}

**🔗 Source:** {report_url}

**⏰ Processed:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
        """
        
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

@app.route('/webhook/market-report', methods=['POST'])
def process_market_report():
    """Main webhook endpoint with AI processing"""
    try:
        # Get email data from Zapier webhook
        email_data = request.json
        email_subject = email_data.get('subject', 'Market Report')
        email_body = email_data.get('body_html', '') or email_data.get('body', '')
        
        print(f"Processing email: {email_subject}")
        
        # Step 1: Extract URL from email
        report_url = extract_url_from_email(email_body)
        if not report_url:
            return jsonify({"error": "No URL found in email"}), 400
        
        print(f"Found report URL: {report_url}")
        
        # Run async operations
        async def process_async():
            # Step 2: Login and fetch report using Playwright
            html_content = await login_and_fetch_report(report_url)
            
            # Step 3: Extract main content
            main_content = extract_main_content(html_content)
            
            if len(main_content) < 100:
                raise Exception("Content too short, extraction may have failed")
            
            # Step 4: AI Translation and Summarization
            ai_result = await ai_translate_and_summarize(main_content)
            
            # Step 5: Save to Notion
            notion_success = save_to_notion(email_subject, ai_result, report_url)
            
            # Step 6: Send Telegram notification
            telegram_success = await send_telegram_notification(email_subject, ai_result, report_url)
            
            return {
                "ai_result": ai_result,
                "notion_success": notion_success,
                "telegram_success": telegram_success
            }
        
        # Run the async process
        result = asyncio.run(process_async())
        
        return jsonify({
            "status": "success",
            "message": "Report processed successfully with AI",
            "notion_saved": result["notion_success"],
            "telegram_sent": result["telegram_success"],
            "report_url": report_url,
            "original_language": result["ai_result"].get("original_language"),
            "summary_length": len(result["ai_result"].get("summary", ""))
        })
        
    except Exception as e:
        print(f"Error processing report: {e}")
        
        # Send error notification
        try:
            asyncio.run(bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"❌ **Error Processing Market Report**\n\nError: {str(e)}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
                parse_mode='Markdown'
            ))
        except:
            pass
        
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/test-ai', methods=['POST'])
def test_ai():
    """Test endpoint for AI translation and summarization"""
    test_content = request.json.get('content', 'Test content for AI processing')
    result = asyncio.run(ai_translate_and_summarize(test_content))
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```.now().strftime('%Y-%m-%d %H:%M')}
        """
        
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='Markdown'
        )
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

@app.route('/webhook/market-report', methods=['POST'])
def process_market_report():
    """Main webhook endpoint"""
    try:
        # Get email data from webhook
        email_data = request.json
        email_subject = email_data.get('subject', 'Market Report')
        email_body = email_data.get('body', '')
        
        print(f"Processing email: {email_subject}")
        
        # Step 1: Extract URL from email
        report_url = extract_url_from_email(email_body)
        if not report_url:
            return jsonify({"error": "No URL found in email"}), 400
        
        # Step 2: Login and fetch report
        html_content = login_and_fetch_report(report_url)
        
        # Step 3: Extract main content
        main_content = extract_main_content(html_content)
        
        # Step 4: Translate content
        translated_content = translate_content(main_content)
        
        # Step 5: Create summary
        summary = summarize_content(translated_content)
        
        # Step 6: Save to Notion
        notion_success = save_to_notion(email_subject, summary, translated_content, report_url)
        
        # Step 7: Send Telegram notification
        asyncio.run(send_telegram_notification(email_subject, summary, report_url))
        
        return jsonify({
            "status": "success",
            "message": "Report processed successfully",
            "notion_saved": notion_success,
            "report_url": report_url
        })
        
    except Exception as e:
        print(f"Error processing report: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)