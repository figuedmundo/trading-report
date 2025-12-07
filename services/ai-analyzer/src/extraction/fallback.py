"""
Fallback keyword extraction when LLM analysis fails.

Provides a basic fallback response containing the raw text.
"""

from typing import Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FallbackExtractor:
    """Fallback mechanism when LLM analysis fails."""

    def __init__(self):
        """Initialize fallback extractor."""
        pass

    def extract_analysis(self, raw_extracted_text: str) -> Dict[str, Any]:
        """
        Return raw text as analysis response.

        Args:
            raw_extracted_text: Raw text to extract from

        Returns:
            Dict with structure compatible with LLM response
        """
        logger.info(
            "Using fallback extraction (raw text return)",
            extra={"text_length": len(raw_extracted_text)}
        )

        # Simply return the raw text as the response
        result = {
            "response": raw_extracted_text,
            "api_provider": "fallback_keyword",
        }

        return result
