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
