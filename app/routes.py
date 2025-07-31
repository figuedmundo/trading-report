from flask import request, jsonify
from datetime import datetime
from .extractor import extract_url_from_email, extract_main_content
from .scraper import login_and_fetch_report
from .ai import ai_translate_and_summarize
from .notion import save_to_notion
from .notifier import send_telegram_notification
import asyncio

def register_routes(app):

    @app.route('/webhook/market-report', methods=['POST'])
    def process_market_report():
        try:
            email_data = request.json
            subject = email_data.get('subject', 'Market Report')
            body = email_data.get('body_html') or email_data.get('body', '')

            report_url = extract_url_from_email(body)
            if not report_url:
                return jsonify({"error": "No report URL found"}), 400

            async def process():
                html = await login_and_fetch_report(report_url)
                content = extract_main_content(html)
                ai_result = await ai_translate_and_summarize(content)
                notion_ok = save_to_notion(subject, ai_result, report_url)
                telegram_ok = await send_telegram_notification(subject, ai_result, report_url)
                return notion_ok, telegram_ok, ai_result

            notion_ok, telegram_ok, ai_result = asyncio.run(process())

            return jsonify({
                "status": "success",
                "notion_saved": notion_ok,
                "telegram_sent": telegram_ok,
                "summary_length": len(ai_result.get("summary", "")),
                "original_language": ai_result.get("original_language", "unknown")
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})
