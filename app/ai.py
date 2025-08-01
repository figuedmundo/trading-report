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
{content}
"""
    try:
        response = client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_completion_tokens=4096,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None,
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
