import sys
import os
import asyncio
from dotenv import load_dotenv

# Add project root to sys.path so we can import 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai import ai_translate_and_summarize

load_dotenv()

async def test_ai():
    sample_content = "Este es un informe de mercado con datos importantes sobre tendencias y riesgos."

    print("🧠 Testing AI translation and summarization...")

    result = await ai_translate_and_summarize(sample_content)

    print("Result keys:", list(result.keys()))
    print("Result:", result)


if __name__ == "__main__":
    asyncio.run(test_ai())
