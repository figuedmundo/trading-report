"""
LLM analysis orchestration layer.

Handles LLM API calls with 30-second timeout, markdown parsing, thinking metadata
extraction, and error handling. Implements graceful degradation to fallback extraction.
"""

import asyncio
from typing import Dict, Any
import time
from src.llm.provider import get_llm_provider, LLMProvider
from src.config import get_config
from src.utils.logger import get_logger
from src.utils.exceptions import LLMError, InvalidResponseError

logger = get_logger(__name__)


class LLMAnalyzer:
    """Orchestrates LLM analysis with timeout, markdown parsing, and error handling."""

    def __init__(self):
        """Initialize LLM analyzer with configured provider."""
        self.provider: LLMProvider = get_llm_provider()
        self.config = get_config()

    async def analyze(self, raw_extracted_text: str, report_id: str, prompt_type: str = None) -> Dict[str, Any]:
        """
        Analyze extracted text with LLM provider.

        Implements 30-second timeout. On failure, logs error and returns None
        to trigger fallback extraction.

        Workflow:
        1. Call LLM provider (with timeout)
        2. Return raw response + optional metadata

        Args:
            raw_extracted_text: Raw text to analyze
            report_id: Report ID for logging context
            prompt_type: Optional prompt type override ('default', 'custom', 'options', etc.)

        Returns:
            Dict with analysis results including:
            - response: Raw markdown response from LLM
            - api_provider: Provider name
            - thinking_tokens_used: Tokens consumed by thinking (if applicable)
            - thinking_content: Full reasoning trace (if applicable)
            - input_tokens: Input tokens used
            - output_tokens: Output tokens used
            Or None on failure

        Raises:
            LLMError: On LLM API failure (will be caught and logged)
        """
        logger.info(
            "Starting LLM analysis",
            extra={
                "report_id": report_id,
                "content_length": len(raw_extracted_text),
                "provider": self.provider.get_provider_name(),
            }
        )

        start_time = time.time()

        try:
            # Implement 30-second timeout on LLM call (with optional prompt_type override)
            analysis = await asyncio.wait_for(
                self._call_llm(raw_extracted_text, prompt_type=prompt_type),
                timeout=self.config.analysis_timeout
            )

            latency_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "LLM analysis completed successfully",
                extra={
                    "report_id": report_id,
                    "provider": self.provider.get_provider_name(),
                    "latency_ms": latency_ms,
                    "thinking_tokens_used": analysis.get("thinking_tokens_used"),
                    "operations_found": analysis.get("operations_found"),
                }
            )
            return analysis

        except asyncio.TimeoutError:
            logger.warning(
                "LLM analysis timed out - fallback extraction will be used",
                extra={
                    "report_id": report_id,
                    "provider": self.provider.get_provider_name(),
                    "timeout_seconds": self.config.analysis_timeout,
                }
            )
            return None

        except InvalidResponseError as e:
            logger.warning(
                f"LLM returned invalid response - fallback extraction will be used: {e.message}",
                extra={
                    "report_id": report_id,
                    "provider": self.provider.get_provider_name(),
                    "error_code": e.error_code,
                }
            )
            return None

        except LLMError as e:
            logger.warning(
                f"LLM API error - fallback extraction will be used: {e.message}",
                extra={
                    "report_id": report_id,
                    "provider": self.provider.get_provider_name(),
                    "error_code": e.error_code,
                }
            )
            return None

        except Exception as e:
            logger.warning(
                f"Unexpected LLM error - fallback extraction will be used: {str(e)}",
                extra={
                    "report_id": report_id,
                    "provider": self.provider.get_provider_name(),
                }
            )
            return None

    async def _call_llm(self, content: str, prompt_type: str = None) -> Dict[str, Any]:
        """
        Call LLM provider and return raw response.

        Handles:
        - Provider API call with optional prompt_type override
        - Response validation
        - Thinking metadata extraction

        Args:
            content: Content to analyze
            prompt_type: Optional prompt type override

        Returns:
            Analysis result dict with raw response and metadata

        Raises:
            LLMError: On API failure
            InvalidResponseError: On malformed response
        """
        try:
            # Use provided prompt_type or fall back to config
            effective_prompt_type = prompt_type or self.config.prompt_type

            # Call provider's async method
            provider_response = await self.provider.analyze(content, prompt_type=effective_prompt_type)

            # Validate response structure
            if not isinstance(provider_response, dict):
                raise InvalidResponseError(
                    "LLM returned non-dict response",
                    context={"response_type": type(provider_response).__name__}
                )

            # Check required fields from provider
            required_fields = ["response", "api_provider"]
            for field in required_fields:
                if field not in provider_response:
                    raise InvalidResponseError(
                        f"LLM response missing required field: {field}",
                        context={"missing_field": field}
                    )

            # Get raw response (markdown as returned by LLM)
            response_text = provider_response.get("response", "")

            # Log thinking efficiency if thinking was used
            thinking_tokens_used = provider_response.get("thinking_tokens_used")
            thinking_budget = getattr(self.config, 'thinking_budget_tokens', 5000)
            if thinking_tokens_used and thinking_budget > 0:
                efficiency_ratio = thinking_tokens_used / thinking_budget
                logger.info(
                    "Thinking token usage",
                    extra={
                        "thinking_tokens_used": thinking_tokens_used,
                        "thinking_budget": thinking_budget,
                        "efficiency_ratio": efficiency_ratio,
                    }
                )

            # Return raw response with metadata (no parsing/section extraction)
            return {
                "response": response_text,  # Raw markdown as-is
                "api_provider": provider_response.get("api_provider", "unknown"),
                "thinking_budget_tokens": getattr(self.config, 'thinking_budget_tokens', 5000),
                "thinking_tokens_used": thinking_tokens_used,
                "thinking_content": provider_response.get("thinking"),
                "model_name": self.config.llm_model,
                "input_tokens": provider_response.get("input_tokens"),
                "output_tokens": provider_response.get("output_tokens"),
            }

        except InvalidResponseError:
            raise

        except Exception as e:
            raise LLMError(
                f"LLM API call failed: {str(e)}",
                context={"original_error": str(e)}
            )

