from dotenv import load_dotenv
import os
import logging
from flask import Flask
from .config import Config
from .routes import api

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
print("ENV LOADED:", os.getenv("GROQ_API_KEY"))

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Register blueprints
    app.register_blueprint(api, url_prefix='/api')
    
    return app