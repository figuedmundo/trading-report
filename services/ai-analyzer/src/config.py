"""
Environment configuration management.

Loads and validates environment variables from .env file.
Provides centralized access to all configuration values.
"""

import os
from typing import Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration from environment variables."""

    # LLM Provider & Model Configuration
    ai_provider: Optional[str] = os.getenv("AI_PROVIDER")  # Optional: explicit provider override
    llm_model: Optional[str] = os.getenv("LLM_MODEL")  # Required: model identifier
    thinking_budget_tokens: int = int(os.getenv("THINKING_BUDGET_TOKENS", "5000"))
    prompt_type: str = os.getenv("PROMPT_TYPE", "default")  # Prompt template to use
    enable_online_search: bool = os.getenv("ENABLE_ONLINE_SEARCH", "false").lower() == "true"

    # AI Provider Configuration (backward compatibility)
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")

    # Service Configuration
    service_port: int = int(os.getenv("SERVICE_PORT", "8002"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    analysis_timeout: int = int(os.getenv("ANALYSIS_TIMEOUT", "30"))

    # Database Configuration
    database_url: Optional[str] = os.getenv("DATABASE_URL")

    @classmethod
    def validate_config(cls) -> bool:
        """
        Validate that all required configuration is set.

        Returns True if valid, False otherwise.
        """
        config = get_config()

        # Validate LLM_MODEL is set
        if not config.llm_model:
            logger.error(
                "Configuration error: LLM_MODEL environment variable not set. "
                "Example: claude-3-5-sonnet-20241022, mixtral-8x7b-32768, or gemini-2.0-flash"
            )
            return False

        # Validate thinking budget tokens range
        if config.thinking_budget_tokens < 1000 or config.thinking_budget_tokens > 32000:
            logger.error(
                f"Configuration error: THINKING_BUDGET_TOKENS must be between 1000 and 32000, "
                f"got {config.thinking_budget_tokens}"
            )
            return False

        # Validate DATABASE_URL is set
        if not config.database_url:
            logger.error("Configuration error: DATABASE_URL environment variable not set")
            return False

        return True


def get_config() -> Config:
    """Get the current configuration instance."""
    return Config()


def validate_config() -> bool:
    """
    Validate that all required configuration is set.

    Returns True if valid, False otherwise. Kept for backward compatibility.
    """
    return Config.validate_config()
