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
        send_email = data.get("send_email", True)
        send_telegram_notification = data.get("send_telegram_notification", True)
        
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
        telegram_success = False
        if send_telegram_notification: 
            telegram_success = telegram_notifier.send_notification(full_response, notion_url)
        
        # Send email
        email_success = False
        if send_email:
            email_success = email_notifier.send_report_email(full_response, target_url)
        
        # Prepare response
        response = {
            'success': True,
            'report_title': scrape_report['title'],
            'source_url': target_url,
            'notion_success': notion_result['success'],
            'telegram_success': telegram_success,
            'email_success': email_success,
            'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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

@api.route('/test-scraper', methods=['POST'])
def test_scraper():
    """Test endpoint for scraping functionality"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        result = scrape_report_wrapper(url)
        
        # Return limited content to avoid large responses
        if result['success']:
            result["text_length"] = len(result['text_content'])
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

@api.route('/test-telegram', methods=['POST'])
def test_telegram():
    """Test endpoint for Telegram notifications"""
    try:
        sample_data = {
            'metadata': {
                'title': 'Test Market Report',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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