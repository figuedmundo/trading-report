import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Pro Trading Skills
    PRO_USERNAME = os.getenv('PRO_USERNAME')
    PRO_PASSWORD = os.getenv('PRO_PASSWORD')

    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Groq AI settings
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_MODEL = "moonshotai/kimi-k2-instruct"
    
    # Notion settings
    NOTION_API_KEY = os.getenv('NOTION_API_KEY')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    
    # Telegram settings
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Email settings
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
    
    # Scraping settings
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')