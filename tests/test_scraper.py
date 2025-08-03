import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.scraper import scrape_report_wrapper, WebScraper
from app.extractor import ContentExtractor

content_extractor = ContentExtractor()
web_scraper = WebScraper()

report_url = "https://protradingskills.com/analysis/instrucciones-antes-de-la-conferencia-de-la-fed-importante-ver-ya/"

load_dotenv()

def test_scraper():
    print("🔍 Running scraper test...")
    try:
        report = scrape_report_wrapper(report_url)
        print(report)

        images = web_scraper._get_images(report.get("html_content"))
        print(images)
    except Exception as e:
        print("❌ Scraper test failed with error:", e)


if __name__ == "__main__":
    test_scraper()
