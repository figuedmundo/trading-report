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
from src.extraction import parse_markdown_sections, extract_trading_operations, extract_section

logger = get_logger(__name__)


class LLMAnalyzer:
    """Orchestrates LLM analysis with timeout, markdown parsing, and error handling."""

    def __init__(self):
        """Initialize LLM analyzer with configured provider."""
        self.provider: LLMProvider = get_llm_provider()
        self.config = get_config()

    async def analyze(self, raw_extracted_text: str, report_id: str) -> Dict[str, Any]:
        """
        Analyze extracted text with LLM provider.

        Implements 30-second timeout. On failure, logs error and returns None
        to trigger fallback extraction.

        Workflow:
        1. Call LLM provider (with timeout)
        2. Parse markdown sections from response
        3. Extract trading operations and metadata
        4. Return complete analysis dict with all metadata

        Args:
            raw_extracted_text: Raw text to analyze
            report_id: Report ID for logging context

        Returns:
            Dict with analysis results including:
            - summary: Executive summary
            - market_insights: List of insights
            - trading_operations: List of trading operations (if found)
            - operations_found: Boolean indicating if operations were extracted
            - thinking_tokens_used: Tokens consumed by thinking (if applicable)
            - thinking_content: Full reasoning trace (if applicable)
            - input_tokens: Input tokens used
            - output_tokens: Output tokens used
            - api_provider: Provider name
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
            # Implement 30-second timeout on LLM call
            analysis = await asyncio.wait_for(
                self._call_llm(raw_extracted_text),
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

    async def _call_llm(self, content: str) -> Dict[str, Any]:
        """
        Call LLM provider and parse response.

        Handles:
        - Provider API call
        - Response validation
        - Markdown section parsing
        - Trading operations extraction
        - Thinking metadata extraction

        Args:
            content: Content to analyze

        Returns:
            Analysis result dict with all metadata

        Raises:
            LLMError: On API failure
            InvalidResponseError: On malformed response
        """
        try:
            # Call provider's async method with configured prompt type
            provider_response = await self.provider.analyze(content, prompt_type=self.config.prompt_type)

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

            # Extract markdown sections from response text
            response_text = provider_response.get("response", "")
            sections = parse_markdown_sections(response_text)

            # Extract summary (required field in parsed response)
            summary = extract_section(sections, "summary").strip()
            if not summary:
                raise InvalidResponseError(
                    "No summary section found in LLM response",
                    context={"sections_found": list(sections.keys())}
                )

            # Extract market insights (optional)
            market_analysis = extract_section(sections, "market analysis", "market observations")
            market_insights = [market_analysis] if market_analysis.strip() else []

            # Extract trading operations
            operations_section = extract_section(
                sections,
                "trading operations",
                "trading signals"
            )
            trading_operations, operations_found = extract_trading_operations(
                operations_section,
                context_text=response_text
            )

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

            # Build complete analysis response
            return {
                "summary": summary,
                "trading_signals": trading_operations,
                "market_insights": market_insights,
                "symbols_mentioned": self._extract_symbols(response_text),
                "price_targets": {},  # Could be enhanced to parse from response
                "api_provider": provider_response.get("api_provider", "unknown"),
                "thinking_budget_tokens": getattr(self.config, 'thinking_budget_tokens', 5000),
                "thinking_tokens_used": thinking_tokens_used,
                "thinking_content": provider_response.get("thinking"),
                "operations_found": operations_found,
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

    def _extract_symbols(self, text: str) -> list:
        """
        Extract trading symbols from response text.

        Simple heuristic: looks for common symbol patterns.
        Could be enhanced with better NLP in future.

        Args:
            text: Text to search for symbols

        Returns:
            List of symbols found
        """
        import re

        # Pattern for common stock symbols: 1-5 uppercase letters
        # e.g., AAPL, MSFT, BTC, ETH
        pattern = r'\b([A-Z]{1,5})\b'
        matches = re.findall(pattern, text)

        # Filter out common words that aren't symbols
        common_words = {'THE', 'AND', 'FOR', 'WITH', 'FROM', 'THAT', 'THIS', 'HAVE', 'WILL', 'CAN', 'SHOULD', 'COULD', 'WOULD', 'REPORT', 'ANALYSIS', 'MARKET', 'TRADING', 'PRICE', 'TIME', 'RISK', 'RETURN'}
        symbols = [m for m in matches if m not in common_words]

        # Return unique symbols, preserving order
        seen = set()
        unique_symbols = []
        for symbol in symbols:
            if symbol not in seen:
                seen.add(symbol)
                unique_symbols.append(symbol)

        return unique_symbols[:20]  # Limit to top 20 symbols
