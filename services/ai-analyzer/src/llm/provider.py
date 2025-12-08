"""
LLM provider abstraction layer.

Supports Anthropic Claude, Groq, and Google Gemini APIs with automatic provider
selection based on model name prefix. Implements extended thinking capabilities
for supported providers.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Type
from src.utils.logger import get_logger
from src.utils.exceptions import ConfigurationError
from src.llm.prompts import get_prompt

logger = get_logger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def analyze(self, content: str, prompt_type: str = "default") -> Dict[str, Any]:
        """
        Analyze content and return structured response.

        Args:
            content: Raw extracted text to analyze
            prompt_type: Prompt template to use (e.g., "default", "detailed", "conservative")

        Returns:
            Dict with analysis results including:
            - response: markdown text from LLM
            - thinking: thinking content (if enabled, else None)
            - thinking_tokens_used: tokens consumed by thinking (if available)
            - input_tokens: input tokens used
            - output_tokens: output tokens used
            - api_provider: provider name
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name for logging/response."""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider with extended thinking support."""

    def __init__(self, api_key: str, thinking_budget_tokens: int = 5000, model_name: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key for authentication
            thinking_budget_tokens: Budget for extended thinking
            model_name: Claude model to use (default: claude-3-5-sonnet-20241022)
        """
        self.api_key = api_key
        self.thinking_budget_tokens = thinking_budget_tokens
        self.model_name = model_name
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ConfigurationError(
                "anthropic library not installed. Install with: pip install anthropic",
                context={"provider": "anthropic"}
            )

    async def analyze(self, content: str, prompt_type: str = "default") -> Dict[str, Any]:
        """
        Analyze content using Claude API with extended thinking.

        Args:
            content: Raw extracted text to analyze
            prompt_type: Prompt template to use

        Returns:
            Dict with analysis results
        """
        prompt = get_prompt(content, prompt_type=prompt_type)
        logger.debug(f"Generated prompt for Anthropic: {prompt[:2000]}...")

        try:
            # Build thinking config if budget > 0
            thinking_config = None
            if self.thinking_budget_tokens > 0:
                thinking_config = {
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget_tokens
                }

            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=8192,
                temperature=0,
                thinking=thinking_config,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract response content and thinking
            analysis_text = ""
            thinking_content = None
            thinking_tokens_used = None

            for block in response.content:
                if block.type == "text":
                    analysis_text = block.text
                elif block.type == "thinking":
                    thinking_content = block.thinking
                    # Try to get thinking tokens from usage
                    if hasattr(response, 'usage') and hasattr(response.usage, 'cache_creation_input_tokens'):
                        thinking_tokens_used = response.usage.cache_creation_input_tokens

            return {
                "response": analysis_text,
                "thinking": thinking_content,
                "thinking_tokens_used": thinking_tokens_used,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "api_provider": "anthropic"
            }

        except Exception as e:
            from src.utils.exceptions import LLMError
            raise LLMError(
                f"Anthropic API call failed: {str(e)}",
                context={"original_error": str(e), "provider": "anthropic"}
            )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "anthropic"


class GroqProvider(LLMProvider):
    """Groq API provider."""

    def __init__(self, api_key: str, thinking_budget_tokens: int = 5000, model_name: str = "mixtral-8x7b-32768"):
        """
        Initialize Groq provider.

        Args:
            api_key: Groq API key for authentication
            thinking_budget_tokens: Budget for extended thinking (not supported by Groq, ignored)
            model_name: Groq model to use (default: mixtral-8x7b-32768)
        """
        self.api_key = api_key
        self.thinking_budget_tokens = thinking_budget_tokens
        self.model_name = model_name
        try:
            from groq import Groq
            self.client = Groq(api_key=api_key)
        except ImportError:
            raise ConfigurationError(
                "groq library not installed. Install with: pip install groq",
                context={"provider": "groq"}
            )

        # Log that thinking is not available for Groq
        if thinking_budget_tokens > 0:
            logger.info(
                "Extended thinking not available for Groq provider - thinking budget ignored",
                extra={"provider": "groq", "thinking_budget_tokens": thinking_budget_tokens}
            )

    async def analyze(self, content: str, prompt_type: str = "default") -> Dict[str, Any]:
        """
        Analyze content using Groq API.

        Args:
            content: Raw extracted text to analyze
            prompt_type: Prompt template to use

        Returns:
            Dict with analysis results
        """
        prompt = get_prompt(content, prompt_type=prompt_type)
        logger.debug(f"Generated prompt for Groq: {prompt[:2000]}...")

        # Get search configuration
        from src.config import get_config
        config = get_config()

        try:
            # Detect if using a reasoning model (openai/gpt-oss-120b, deepseek-r1, etc.)
            is_reasoning_model = any(k in self.model_name.lower() for k in ["openai", "deepseek", "reasoning"])
            
            params = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
            }

            # Add tools if online search is enabled
            if config.enable_online_search:
                params["tools"] = [{"type": "browser_search"}]
                logger.info("Online search enabled for Groq request")

            if is_reasoning_model:
                # Tuning for reasoning models
                params["max_completion_tokens"] = 8192
                params["temperature"] = 1
                params["reasoning_effort"] = "high"
                # Remove max_tokens if present in favor of max_completion_tokens
            else:
                # Standard models (Mixtral, Llama 3)
                params["max_tokens"] = 8192
                params["temperature"] = 0

            response = self.client.chat.completions.create(**params)

            result_text = response.choices[0].message.content.strip()

            return {
                "response": result_text,
                "thinking": None, # Groq reasoning content usually folded into response or not returned separately yet
                "thinking_tokens_used": None,
                "input_tokens": getattr(response.usage, 'prompt_tokens', None),
                "output_tokens": getattr(response.usage, 'completion_tokens', None),
                "api_provider": "groq"
            }

        except Exception as e:
            from src.utils.exceptions import LLMError
            raise LLMError(
                f"Groq API call failed: {str(e)}",
                context={"original_error": str(e), "provider": "groq"}
            )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "groq"


class GoogleProvider(LLMProvider):
    """Google Gemini API provider with extended thinking support using new google-genai SDK."""

    def __init__(self, api_key: str, thinking_budget_tokens: int = 5000, model_name: str = "gemini-2.0-flash"):
        """
        Initialize Google provider.

        Args:
            api_key: Google API key for authentication
            thinking_budget_tokens: Budget for extended thinking (if supported)
            model_name: Gemini model to use (default: gemini-2.0-flash)
        """
        self.api_key = api_key
        self.thinking_budget_tokens = thinking_budget_tokens
        self.model_name = model_name
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
        except ImportError:
            raise ConfigurationError(
                "google-genai library not installed. Install with: pip install google-genai",
                context={"provider": "google"}
            )

    async def analyze(self, content: str, prompt_type: str = "default") -> Dict[str, Any]:
        """
        Analyze content using Google Gemini API with new google-genai SDK.

        Args:
            content: Raw extracted text to analyze
            prompt_type: Prompt template to use

        Returns:
            Dict with analysis results
        """
        prompt = get_prompt(content, prompt_type=prompt_type)
        logger.debug(f"Generated prompt for Google: {prompt[:2000]}...")

        try:
            from google.genai import types

            # Build config with thinking if budget > 0
            config = types.GenerateContentConfig(
                max_output_tokens=8192,
                temperature=0,
            )

            # Add thinking config if supported and budget > 0
            if self.thinking_budget_tokens > 0:
                try:
                    config.thinking_config = types.ThinkingConfig(
                        budget_tokens=self.thinking_budget_tokens
                    )
                    logger.info(
                        "Extended thinking enabled for Gemini",
                        extra={"model": self.model_name, "budget": self.thinking_budget_tokens}
                    )
                except Exception:
                    # If thinking not supported, continue without it
                    logger.info("Extended thinking not available for this Gemini model")

            # Call Gemini API using new SDK
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )

            # Extract text from response
            result_text = response.text if hasattr(response, 'text') else str(response)

            # Extract usage metadata
            input_tokens = None
            output_tokens = None
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count

            return {
                "response": result_text,
                "thinking": None,  # Future: Extract thinking from response if available
                "thinking_tokens_used": None,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "api_provider": "google",
                "model_name": self.model_name,
            }

        except Exception as e:
            from src.utils.exceptions import LLMError
            logger.error(
                "Google Gemini API call failed",
                extra={"error": str(e), "provider": "google", "model": self.model_name}
            )
            raise LLMError(
                f"Google Gemini API call failed: {str(e)}",
                context={"original_error": str(e), "provider": "google", "model": self.model_name}
            )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "google"


def get_provider_from_model(model_name: str) -> Tuple[Type[LLMProvider], str]:
    """
    Detect LLM provider from model name prefix.

    Args:
        model_name: Model identifier (e.g., "claude-3-5-sonnet-20241022")

    Returns:
        Tuple of (ProviderClass, provider_name)

    Raises:
        ConfigurationError: If provider not detected or API key missing
    """
    if not model_name:
        raise ConfigurationError(
            "LLM_MODEL environment variable not set. "
            "Example models: claude-3-5-sonnet-20241022, mixtral-8x7b-32768, gemini-2.0-flash",
            context={"model_name": model_name}
        )

    # Extract prefix (before first digit or hyphen)
    prefix = model_name.split('-')[0].lower()

    provider_map = {
        'claude': (AnthropicProvider, 'ANTHROPIC_API_KEY'),
        'mixtral': (GroqProvider, 'GROQ_API_KEY'),
        'llama': (GroqProvider, 'GROQ_API_KEY'),
        'gemma': (GroqProvider, 'GROQ_API_KEY'),
        'openai': (GroqProvider, 'GROQ_API_KEY'),
        'deepseek': (GroqProvider, 'GROQ_API_KEY'),
        'gemini': (GoogleProvider, 'GOOGLE_API_KEY'),
    }

    if prefix not in provider_map:
        raise ConfigurationError(
            f"Unknown model prefix: {prefix}. "
            f"Supported prefixes: {', '.join(provider_map.keys())}. "
            f"Example models: claude-3-5-sonnet-20241022, mixtral-8x7b-32768, openai/gpt-oss-120b, gemini-2.0-flash",
            context={"model_name": model_name, "prefix": prefix}
        )

    provider_class, api_key_var = provider_map[prefix]
    api_key = os.getenv(api_key_var)

    if not api_key:
        raise ConfigurationError(
            f"API key {api_key_var} required for {prefix} models. "
            f"Set {api_key_var} environment variable or choose a different LLM_MODEL",
            context={"model_name": model_name, "provider": prefix, "required_key": api_key_var}
        )

    logger.info(
        f"Detected provider from model name",
        extra={"model_name": model_name, "prefix": prefix, "provider": prefix}
    )

    return provider_class, prefix


def get_llm_provider(ai_provider: str = None, model_name: str = None) -> LLMProvider:
    """
    Factory function to get LLM provider based on configuration or overrides.

    Supports two modes:
    1. Auto-detection: Uses LLM_MODEL prefix to detect provider (recommended)
    2. Explicit: Uses AI_PROVIDER to override detection (optional)

    Can be overridden by passing ai_provider and/or model_name arguments.

    Args:
        ai_provider: Optional override for provider name (anthropic, groq, google)
        model_name: Optional override for model name

    Returns:
        Configured LLMProvider instance

    Raises:
        ConfigurationError: If required variables not set or API key missing
    """
    from src.config import get_config

    config = get_config()

    # Default models for each provider (fallback if only provider is specified)
    default_models = {
        'anthropic': 'claude-3-5-sonnet-20241022',
        'groq': 'mixtral-8x7b-32768',
        'google': 'gemini-2.0-flash',
    }

    # Determine effective configuration
    effective_provider_name = (ai_provider or config.ai_provider or "").lower()
    effective_model_name = model_name or config.llm_model

    # If provider is switched but model isn't, try to set a safe default model for that provider
    # ONLY if the current model doesn't match the new provider
    if ai_provider and not model_name:
        # Check if current configured model is compatible with new provider
        try:
            # fast check if model prefix matches new provider
            _, detected_prefix = get_provider_from_model(effective_model_name)
            provider_map = {
                'anthropic': 'claude',
                'groq': 'mixtral',  # incomplete map but handled in get_provider_from_model
                'google': 'gemini'
            }
            # This check is complex because get_provider_from_model handles prefixes
            # Simpler: if explicitly switching provider, use that provider's default model
            # unless the current model is KNOWN to be compatible.
            # To be safe: if ai_provider is explicit, and no model_name given, use default for that provider.
            if effective_provider_name in default_models:
                effective_model_name = default_models[effective_provider_name]
        except Exception:
            # If current model name is invalid for some reason, use default
            if effective_provider_name in default_models:
                effective_model_name = default_models[effective_provider_name]

    # Validate LLM_MODEL is set (either via arg, config, or default logic)
    if not effective_model_name:
        raise ConfigurationError(
            "LLM_MODEL not set and could not be inferred.",
            context={}
        )

    # Determine provider class
    if effective_provider_name:
        # Explicit provider override
        provider_map = {
            'anthropic': (AnthropicProvider, 'ANTHROPIC_API_KEY'),
            'groq': (GroqProvider, 'GROQ_API_KEY'),
            'google': (GoogleProvider, 'GOOGLE_API_KEY'),
        }

        if effective_provider_name not in provider_map:
            # If we have a model name, try to auto-detect from it as fallback
            try:
                provider_class, provider_name = get_provider_from_model(effective_model_name)
            except ConfigurationError:
                raise ConfigurationError(
                    f"Unknown AI_PROVIDER: {effective_provider_name}. "
                    f"Options: anthropic, groq, google",
                    context={"ai_provider": effective_provider_name}
                )
        else:
            provider_class, api_key_var = provider_map[effective_provider_name]
            provider_name = effective_provider_name
            logger.info(
                "Using explicitly configured provider",
                extra={"provider": provider_name, "model": effective_model_name}
            )
    else:
        # Auto-detect from model name
        provider_class, provider_name = get_provider_from_model(effective_model_name)

    # Get API key for detected/explicit provider
    api_key_map = {
        'anthropic': config.anthropic_api_key,
        'groq': config.groq_api_key,
        'google': config.google_api_key,
    }

    api_key = api_key_map.get(provider_name)

    if not api_key:
        raise ConfigurationError(
            f"API key required for {provider_name} provider. "
            f"Check environment variables and LLM_MODEL setting",
            context={"provider": provider_name, "model_name": effective_model_name}
        )

    # Instantiate provider with thinking budget and model name
    # Use config thinking budget, unless we want to override that too?
    # For now, keep thinking budget from config as it's a safety setting.
    provider = provider_class(api_key, thinking_budget_tokens=config.thinking_budget_tokens, model_name=effective_model_name)

    logger.info(
        "LLM provider initialized",
        extra={
            "provider": provider_name,
            "model": effective_model_name,
            "thinking_budget_tokens": config.thinking_budget_tokens
        }
    )

    return provider
