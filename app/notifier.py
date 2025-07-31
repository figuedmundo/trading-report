import telegram
from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from datetime import datetime

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

async def send_telegram_notification(title, ai_result, url):
    message = f"""
📣 *New Market Report*

*{title}*

*Summary:* {ai_result['summary'][:400]}...
*Outlook:* {ai_result['market_outlook'][:200]}
*Risk:* {ai_result['risk_factors'][:200]}

🔗 {url}
🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
"""
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='Markdown')
        return True
    except Exception as e:
        print("Telegram error:", e)
        return False
