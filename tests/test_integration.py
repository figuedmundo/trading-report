import sys
import os
import asyncio
from dotenv import load_dotenv

# Add project root to path to import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.scraper import login_and_fetch_report
from app.ai import ai_translate_and_summarize

load_dotenv()

# Replace this with a real or staging URL from your email
report_url = "https://protradingskills.com/analysis/instrucciones-antes-de-la-conferencia-de-la-fed-importante-ver-ya/"


async def test_scraper_ai_integration():
    print("🔗 Testing integration...")

    try:
        report = await login_and_fetch_report(report_url)
        result = await ai_translate_and_summarize(report)

        # Validate required keys
        expected_keys = [
            "original_language",
            "translated_content",
            "summary",
            "key_metrics",
            "market_outlook",
            "risk_factors",
        ]
        missing = [k for k in expected_keys if k not in result]
        if missing:
            print(f"❌ Missing keys in AI result: {missing}")
        else:
            print("✅ AI result contains all expected keys")
            print("translated:", result["translated_content"])
            print("Summary:", result["summary"])
            print("key_metrics: ", result["key_metrics"])

    except Exception as e:
        print("❌ Integration test failed:", e)

if __name__ == "__main__":
    asyncio.run(test_scraper_ai_integration())
