"""
LLM provider abstraction layer.

Supports both Anthropic Claude and Groq APIs with provider selection logic.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any
from src.utils.logger import get_logger
from src.utils.exceptions import ConfigurationError

logger = get_logger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def analyze(self, content: str) -> Dict[str, Any]:
        """
        Analyze content and return structured response.

        Args:
            content: Raw extracted text to analyze

        Returns:
            Dict with analysis results
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name for logging/response."""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str):
        """Initialize Anthropic provider."""
        self.api_key = api_key
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ConfigurationError(
                "anthropic library not installed. Install with: pip install anthropic",
                context={"provider": "anthropic"}
            )

    async def analyze(self, content: str) -> Dict[str, Any]:
        """
        Analyze content using Claude API.

        Args:
            content: Raw extracted text to analyze

        Returns:
            Dict with analysis results
        """
        import json

        prompt = f"""Analyze the following trading report and extract:
1. A 200-300 word executive summary
2. Trading signals (BUY/SELL/HOLD) with symbol, prices, timeframe, and confidence
3. Market insights (key observations)
4. Symbols/tickers mentioned
5. Price targets for each symbol

Return as JSON with these keys: summary, trading_signals, market_insights, symbols_mentioned, price_targets

REPORT CONTENT:
{content}

Return ONLY valid JSON, no markdown formatting."""

        # Note: Using sync client but wrapping for compatibility
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        result_text = response.content[0].text.strip()

        # Clean up JSON if wrapped in markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()

        analysis = json.loads(result_text)
        analysis["api_provider"] = "anthropic"
        return analysis

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "anthropic"


class GroqProvider(LLMProvider):
    """Groq API provider."""

    def __init__(self, api_key: str):
        """Initialize Groq provider."""
        self.api_key = api_key
        try:
            from groq import Groq
            self.client = Groq(api_key=api_key)
        except ImportError:
            raise ConfigurationError(
                "groq library not installed. Install with: pip install groq",
                context={"provider": "groq"}
            )

    async def analyze(self, content: str) -> Dict[str, Any]:
        """
        Analyze content using Groq API.

        Args:
            content: Raw extracted text to analyze

        Returns:
            Dict with analysis results
        """
        import json

        prompt = f"""Analyze the following trading report and extract:
1. A 200-300 word executive summary
2. Trading signals (BUY/SELL/HOLD) with symbol, prices, timeframe, and confidence
3. Market insights (key observations)
4. Symbols/tickers mentioned
5. Price targets for each symbol

Return as JSON with these keys: summary, trading_signals, market_insights, symbols_mentioned, price_targets

REPORT CONTENT:
{content}

Return ONLY valid JSON, no markdown formatting."""

        # Note: Using sync client but wrapping for compatibility
        response = self.client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
        )

        result_text = response.choices[0].message.content.strip()

        # Clean up JSON if wrapped in markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()

        analysis = json.loads(result_text)
        analysis["api_provider"] = "groq"
        return analysis

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "groq"


def get_llm_provider() -> LLMProvider:
    """
    Factory function to get LLM provider based on environment variables.

    Checks ANTHROPIC_API_KEY first, falls back to GROQ_API_KEY.

    Returns:
        Configured LLMProvider instance

    Raises:
        ConfigurationError: If no API keys are configured
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    if anthropic_key:
        logger.info("Using Anthropic provider for LLM analysis")
        return AnthropicProvider(anthropic_key)
    elif groq_key:
        logger.info("Using Groq provider for LLM analysis")
        return GroqProvider(groq_key)
    else:
        raise ConfigurationError(
            "No LLM API key found. Set ANTHROPIC_API_KEY or GROQ_API_KEY",
            context={"provider": "none"}
        )
