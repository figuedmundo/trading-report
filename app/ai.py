from groq import Groq
from .config import GROQ_API_KEY
import json

client = Groq(api_key=GROQ_API_KEY)

async def ai_translate_and_summarize(content):
    prompt = f"""
Translate this market report to English if necessary, and summarize it with:
- Key insights
- Metrics
- Market outlook
- Risk factors

Respond in JSON with keys:
original_language, translated_content, summary, key_metrics, market_outlook, risk_factors

Content:
{content[:8000]}
"""
    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3
        )
        raw = response.choices[0].message.content
        return json.loads(raw)
    except Exception as e:
        print("Groq AI error:", e)
        return {
            "original_language": "unknown",
            "translated_content": content,
            "summary": content[:500],
            "key_metrics": "",
            "market_outlook": "",
            "risk_factors": ""
        }
