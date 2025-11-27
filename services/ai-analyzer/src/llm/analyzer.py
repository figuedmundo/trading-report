"""
LLM analysis orchestration layer.

Handles LLM API calls with 30-second timeout and error handling.
"""

import asyncio
from typing import Dict, Any
from src.llm.provider import get_llm_provider, LLMProvider
from src.config import get_config
from src.utils.logger import get_logger
from src.utils.exceptions import LLMError, InvalidResponseError

logger = get_logger(__name__)


class LLMAnalyzer:
    """Orchestrates LLM analysis with timeout and error handling."""

    def __init__(self):
        """Initialize LLM analyzer with configured provider."""
        self.provider: LLMProvider = get_llm_provider()
        self.config = get_config()

    async def analyze(self, raw_extracted_text: str, report_id: str) -> Dict[str, Any]:
        """
        Analyze extracted text with LLM provider.

        Implements 30-second timeout. On failure, logs error and returns None
        to trigger fallback extraction.

        Args:
            raw_extracted_text: Raw text to analyze
            report_id: Report ID for logging context

        Returns:
            Dict with analysis results including api_provider field, or None on failure

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

        try:
            # Implement 30-second timeout on LLM call
            analysis = await asyncio.wait_for(
                self._call_llm(raw_extracted_text),
                timeout=self.config.analysis_timeout
            )

            logger.info(
                "LLM analysis completed successfully",
                extra={
                    "report_id": report_id,
                    "provider": self.provider.get_provider_name(),
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

    async def _call_llm(self, content: str) -> Dict[str, Any]:
        """
        Call LLM provider (wrapped for async compatibility).

        Args:
            content: Content to analyze

        Returns:
            Analysis result dict

        Raises:
            LLMError: On API failure
            InvalidResponseError: On malformed response
        """
        try:
            # Call provider's async method
            result = await self.provider.analyze(content)

            # Validate response structure
            if not isinstance(result, dict):
                raise InvalidResponseError(
                    "LLM returned non-dict response",
                    context={"response_type": type(result).__name__}
                )

            required_fields = ["summary", "trading_signals", "market_insights", "symbols_mentioned", "price_targets"]
            for field in required_fields:
                if field not in result:
                    raise InvalidResponseError(
                        f"LLM response missing required field: {field}",
                        context={"missing_field": field}
                    )

            return result

        except InvalidResponseError:
            raise

        except Exception as e:
            raise LLMError(
                f"LLM API call failed: {str(e)}",
                context={"original_error": str(e)}
            )
