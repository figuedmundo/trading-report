"""
Confidence scoring for trading signals.

Implements simple 3-tier confidence model for signal reliability assessment.
"""

import re
from typing import Dict, List, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConfidenceScorer:
    """Scores confidence levels for trading signals."""

    def __init__(self):
        """Initialize confidence scorer."""
        pass

    def score_signal(self, signal: Dict[str, Any], text: str) -> Dict[str, Any]:
        """
        Score signal confidence based on text context.

        Returns 0.9 for explicit, 0.6 for implied, 0.3 for passing mention.

        Args:
            signal: Signal dict to score
            text: Original text for context analysis

        Returns:
            Signal dict with confidence_score set
        """
        text_lower = text.lower()
        symbol = signal.get("symbol", "").lower()
        action = signal.get("action", "").upper()

        # Search context around symbol
        confidence = self._calculate_confidence(text_lower, symbol, action)

        signal["confidence_score"] = confidence
        return signal

    def _calculate_confidence(self, text: str, symbol: str, action: str) -> float:
        """
        Calculate confidence score based on text patterns.

        0.9: Explicit recommendation (recommend, strong, buy/sell in close proximity)
        0.6: Implied/pattern-based (uptrend, downtrend, support, resistance)
        0.3: Passing mention (single word match without context)

        Args:
            text: Lowercase text
            symbol: Symbol to search for
            action: BUY, SELL, or HOLD

        Returns:
            Confidence score (0.3, 0.6, or 0.9)
        """
        # Explicit confidence keywords
        explicit_keywords = [
            'strongly recommend',
            'strong buy',
            'strong sell',
            'recommend',
            'definite buy',
            'definite sell',
            'clear signal',
            'confirm',
            'confirmed',
        ]

        # Implied confidence keywords
        implied_keywords = [
            'uptrend',
            'downtrend',
            'support level',
            'resistance level',
            'break above',
            'break below',
            'momentum',
            'pattern',
            'technical signal',
        ]

        # Check for explicit signals
        for keyword in explicit_keywords:
            pattern = rf'{keyword}.*?{symbol}|{symbol}.*?{keyword}'
            if re.search(pattern, text, re.IGNORECASE):
                return 0.9

        # Check action-specific explicit patterns
        action_lower = action.lower()
        if action_lower == 'buy':
            if re.search(rf'strongly?\s+buy.*?{symbol}|{symbol}.*?(?:strong\s+)?buy', text):
                return 0.9
        elif action_lower == 'sell':
            if re.search(rf'strongly?\s+sell.*?{symbol}|{symbol}.*?(?:strong\s+)?sell', text):
                return 0.9

        # Check for implied signals
        for keyword in implied_keywords:
            if re.search(keyword, text):
                # Check if symbol is in same sentence/paragraph
                sentences = re.split(r'[.!?]\n?', text)
                for sentence in sentences:
                    if symbol in sentence and keyword in sentence:
                        return 0.6

        # Check for passing mention (just symbol + action word somewhere)
        if symbol in text:
            if action_lower in text:
                return 0.3

        # Default to lowest confidence
        return 0.3

    def score_signals(self, signals: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """
        Score multiple signals.

        Args:
            signals: List of signal dicts
            text: Original text for context

        Returns:
            List of scored signals
        """
        scored = []
        for signal in signals:
            # Skip if confidence already set and looks valid
            if "confidence_score" in signal and isinstance(signal["confidence_score"], (int, float)):
                if 0.0 <= signal["confidence_score"] <= 1.0:
                    scored.append(signal)
                    continue

            scored.append(self.score_signal(signal, text))

        return scored
