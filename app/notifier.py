import logging
from datetime import datetime
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from .config import Config

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_notification(self, report_data: Dict[str, Any], notion_url: str = None) -> bool:
        """Send Telegram notification about new market report"""
        try:
            metadata = report_data.get('metadata', {})
            analysis = report_data.get('analysis', {})
            
            # Create message
            title = metadata.get('title', 'New Market Report')
            summary = analysis.get('summary', 'Report processed successfully')
            
            message = f"📊 **{title}**\n\n"
            message += f"📝 **Summary:**\n{summary}\n\n"
            
            # Add key insights
            if analysis.get('key_insights'):
                message += "💡 **Key Insights:**\n"
                for insight in analysis['key_insights'][:3]:  # Limit to 3 insights
                    message += f"• {insight}\n"
                message += "\n"
            
            # Add market sentiment
            metrics = analysis.get('market_metrics', {})
            if metrics.get('market_sentiment'):
                sentiment_emoji = {
                    'positive': '📈',
                    'negative': '📉',
                    'neutral': '➡️'
                }
                emoji = sentiment_emoji.get(metrics['market_sentiment'], '➡️')
                message += f"{emoji} **Sentiment:** {metrics['market_sentiment'].title()}\n\n"
            
            # Add Notion link
            if notion_url:
                message += f"🔗 [View in Notion]({notion_url})\n"
            
            message += f"⏰ {metadata.get('timestamp', 'Just now')}"
            
            # Send message
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    def send_error_notification(self, error_message: str, context: str = "") -> bool:
        """Send error notification via Telegram"""
        try:
            message = f"🚨 **Market Report Processing Error**\n\n"
            message += f"**Error:** {error_message}\n"
            if context:
                message += f"**Context:** {context}\n"
            message += f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=15
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
            return False

class EmailNotifier:
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.email_address = Config.EMAIL_ADDRESS
        self.email_password = Config.EMAIL_PASSWORD
        self.recipient_email = Config.RECIPIENT_EMAIL
    
    def send_report_email(self, report_data: Dict[str, Any], source_url: str) -> bool:
        """Send processed report via email"""
        try:
            metadata = report_data.get('metadata', {})
            analysis = report_data.get('analysis', {})
            content = report_data.get('content', {})
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Pro-Trading Skills Report: {metadata.get('title', 'New Report')}"
            msg['From'] = self.email_address
            msg['To'] = self.recipient_email
            
            # Create HTML content
            html_content = self._create_html_email(report_data, source_url)
            
            # Create plain text content
            # text_content = self._create_text_email(report_data, source_url)
            
            # Attach content
            # msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            logger.info("Email sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _create_html_email(self, report_data: Dict[str, Any], source_url: str) -> str:
        """Create HTML email content"""
        metadata = report_data.get('metadata', {})
        analysis = report_data.get('analysis', {})
        content = report_data.get('content', {})
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Market Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; }}
                .insights {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; }}
                .risks {{ background-color: #fff3cd; padding: 15px; border-radius: 5px; }}
                .action-items {{ background-color: #d4edda; padding: 15px; border-radius: 5px; }}
                ul {{ padding-left: 20px; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 {metadata.get('title', 'Market Report')}</h1>
                <p><strong>Source:</strong> <a href="{source_url}">{source_url}</a></p>
                <p><strong>Processed:</strong> {metadata.get('timestamp', 'Just now')}</p>
            </div>
            
            <div class="section">
                <h2>📝 Executive Summary</h2>
                <p>{analysis.get('summary', 'Summary not available')}</p>
            </div> 
        """
        
        # Key Insights
        if analysis.get('key_insights'):
            html += """
            <div class="section insights">
                <h2>💡 Key Insights</h2>
                <ul>
            """
            for insight in analysis['key_insights']:
                html += f"<li>{insight}</li>"
            html += "</ul></div>"
        
        # Market Outlook
        if analysis.get('outlook'):
            html += f"""
            <div class="section">
                <h2>🔮 Market Outlook</h2>
                <p>{analysis['outlook']}</p>
            </div>
            """
        
        # Risk Factors
        if analysis.get('risk_factors'):
            html += """
            <div class="section risks">
                <h2>⚠️ Risk Factors</h2>
                <ul>
            """
            for risk in analysis['risk_factors']:
                html += f"<li>{risk}</li>"
            html += "</ul></div>"
        
        # Action Items
        if analysis.get('action_items'):
            html += """
            <div class="section action-items">
                <h2>✅ Action Items</h2>
                <ul>
            """
            for item in analysis['action_items']:
                html += f"<li>{item}</li>"
            html += "</ul></div>"

        # Original Content
        if content.get('original_html'):
            original_html = content.get('original_html')
            html += f"""
            <div class="section">
                <h2>📄 Original Report </h2>
                <div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; background-color: #f9f9f9;">
                    {original_html}
                </div>
            </div>
            """
        
        # Full Content (truncated)
        if content.get('translated_content'):
            translated = content['translated_content']
            html += f"""
            <div class="section">
                <h2>📄 Full Report (Translated)</h2>
                <div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; background-color: #f9f9f9;">
                    <p>{translated.replace('\n', '<br>')}</p>
                </div>
            </div>
            """
        
        html += """
            <div class="footer">
                <p>This report was automatically processed by the Market Report AI system.</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_text_email(self, report_data: Dict[str, Any], source_url: str) -> str:
        """Create plain text email content"""
        metadata = report_data.get('metadata', {})
        analysis = report_data.get('analysis', {})
        
        text = f"MARKET REPORT: {metadata.get('title', 'New Report')}\n"
        text += "=" * 50 + "\n\n"
        text += f"Source: {source_url}\n"
        text += f"Processed: {metadata.get('timestamp', 'Just now')}\n\n"
        
        text += "EXECUTIVE SUMMARY\n"
        text += "-" * 20 + "\n"
        text += f"{analysis.get('summary', 'Summary not available')}\n\n"
        
        if analysis.get('key_insights'):
            text += "KEY INSIGHTS\n"
            text += "-" * 20 + "\n"
            for insight in analysis['key_insights']:
                text += f"• {insight}\n"
            text += "\n"
        
        if analysis.get('outlook'):
            text += "MARKET OUTLOOK\n"
            text += "-" * 20 + "\n"
            text += f"{analysis['outlook']}\n\n"
        
        if analysis.get('risk_factors'):
            text += "RISK FACTORS\n"
            text += "-" * 20 + "\n"
            for risk in analysis['risk_factors']:
                text += f"• {risk}\n"
            text += "\n"
        
        if analysis.get('action_items'):
            text += "ACTION ITEMS\n"
            text += "-" * 20 + "\n"
            for item in analysis['action_items']:
                text += f"• {item}\n"
            text += "\n"
        
        text += "\n" + "=" * 50 + "\n"
        text += "This report was automatically processed by the Market Report AI system."
        
        return text
