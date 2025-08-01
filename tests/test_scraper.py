import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the 'app' directory to the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.scraper import login_and_fetch_report

# Put a real URL here for testing
report_url = "https://protradingskills.com/analysis/instrucciones-antes-de-la-conferencia-de-la-fed-importante-ver-ya/"

load_dotenv()  # Load .env variables like WEBSITE_USERNAME, WEBSITE_PASSWORD

async def test_scraper():
    print("🔍 Running scraper test...")
    try:
        report = await login_and_fetch_report(report_url)
        print(report)
    except Exception as e:
        print("❌ Scraper test failed with error:", e)

if __name__ == "__main__":
    asyncio.run(test_scraper())
