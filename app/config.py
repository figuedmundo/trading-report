import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Website Authentication
    WEBSITE_USERNAME = os.environ.get('WEBSITE_USERNAME')
    WEBSITE_PASSWORD = os.environ.get('WEBSITE_PASSWORD')
    
    # API Keys
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    # Service IDs
    NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    # AI Settings
    AI_MODEL = os.environ.get('AI_MODEL', 'moonshotai/kimi-k2-instruct')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 8000))
    
    # Security
    WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')
    
    @staticmethod
    def validate_config():
        """Validate required configuration"""
        required_vars = [
            'GROQ_API_KEY', 'NOTION_TOKEN', 'TELEGRAM_BOT_TOKEN',
            'NOTION_DATABASE_ID', 'TELEGRAM_CHAT_ID',
            'WEBSITE_USERNAME', 'WEBSITE_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True