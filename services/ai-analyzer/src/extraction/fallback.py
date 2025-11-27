"""
Fallback keyword extraction when LLM analysis fails.

Implements simple regex-based extraction for signals, symbols, and price targets.
"""

import re
from typing import Dict, List, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FallbackExtractor:
    """Extracts trading signals using keyword matching."""

    def __init__(self):
        """Initialize fallback extractor."""
        pass

    def extract_analysis(self, raw_extracted_text: str) -> Dict[str, Any]:
        """
        Extract analysis using keyword matching.

        Args:
            raw_extracted_text: Raw text to extract from

        Returns:
            Dict with same structure as LLM response
        """
        logger.info(
            "Extracting analysis using fallback keyword extraction",
            extra={"text_length": len(raw_extracted_text)}
        )

        symbols = self._extract_symbols(raw_extracted_text)
        trading_signals = self._extract_signals(raw_extracted_text, symbols)
        price_targets = self._extract_price_targets(raw_extracted_text, symbols)

        # Generate basic summary from content
        summary = self._generate_summary(raw_extracted_text, trading_signals, symbols)

        result = {
            "summary": summary,
            "trading_signals": trading_signals,
            "market_insights": self._extract_insights(raw_extracted_text),
            "symbols_mentioned": symbols,
            "price_targets": price_targets,
            "api_provider": "fallback_keyword",
        }

        return result

    def _extract_symbols(self, text: str) -> List[str]:
        """
        Extract stock tickers/symbols from text.

        Looks for common patterns: 1-5 uppercase letters, common symbols like BTC, ETH.

        Args:
            text: Text to search

        Returns:
            List of unique symbols found
        """
        # Pattern for common tickers (1-5 uppercase letters, numbers)
        pattern = r'\b([A-Z]{1,5})\b'
        matches = re.findall(pattern, text)

        # Filter common stop words that aren't symbols
        stop_words = {
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'CAN', 'YOUR',
            'WILL', 'ONE', 'TWO', 'ALL', 'SHOULD', 'COULD', 'WOULD', 'ALSO',
            'MORE', 'THAN', 'THAT', 'THIS', 'THESE', 'THOSE', 'WHICH', 'WITH',
            'FROM', 'TRADING', 'REPORT', 'ANALYSIS', 'BUY', 'SELL', 'HOLD',
            'SIGNAL', 'STRONG', 'WEAK', 'TARGET', 'PRICE', 'LEVEL', 'SUPPORT',
            'RESISTANCE', 'TREND', 'MARKET', 'SHORT', 'LONG', 'TERM', 'ENTRY',
            'EXIT', 'STOP', 'LOSS', 'PROFIT', 'TAKE', 'RISK', 'REWARD',
        }

        symbols = []
        for symbol in matches:
            if symbol not in stop_words and symbol not in symbols:
                symbols.append(symbol)

        return list(set(symbols))[:20]  # Limit to 20 symbols

    def _extract_signals(self, text: str, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Extract trading signals using keyword matching.

        Looks for buy/sell/hold keywords near symbols.

        Args:
            text: Text to search
            symbols: List of symbols to cross-reference

        Returns:
            List of signal dicts
        """
        signals = []
        text_upper = text.upper()
        text_lower = text.lower()

        # Define signal patterns with confidence levels
        strong_buy_patterns = [
            r'\bstrongly?\s+recommend\s+buy',
            r'\bstrong\s+buy',
            r'\bconfirm\s+buy',
        ]
        strong_sell_patterns = [
            r'\bstrongly?\s+recommend\s+sell',
            r'\bstrong\s+sell',
            r'\bconfirm\s+sell',
        ]
        buy_patterns = [
            r'\bbuy\b',
            r'\bgoing\s+long',
            r'\bupside',
        ]
        sell_patterns = [
            r'\bsell\b',
            r'\bgoing\s+short',
            r'\bdownside',
        ]
        hold_patterns = [
            r'\bhold\b',
            r'\bneutral',
            r'\bno\s+clear\s+signal',
        ]

        # Extract strong signals
        for symbol in symbols:
            # Check for strong buy signals
            for pattern in strong_buy_patterns:
                if re.search(pattern, text_lower) and symbol in text_upper:
                    signals.append({
                        "action": "BUY",
                        "symbol": symbol,
                        "entry_price": None,
                        "target_price": None,
                        "stop_loss": None,
                        "timeframe": "medium-term",
                        "confidence_score": 0.9,
                    })
                    break

            # Check for strong sell signals
            for pattern in strong_sell_patterns:
                if re.search(pattern, text_lower) and symbol in text_upper:
                    signals.append({
                        "action": "SELL",
                        "symbol": symbol,
                        "entry_price": None,
                        "target_price": None,
                        "stop_loss": None,
                        "timeframe": "medium-term",
                        "confidence_score": 0.9,
                    })
                    break

            # Check for regular buy signals
            for pattern in buy_patterns:
                if re.search(pattern, text_lower) and symbol in text_upper:
                    signals.append({
                        "action": "BUY",
                        "symbol": symbol,
                        "entry_price": None,
                        "target_price": None,
                        "stop_loss": None,
                        "timeframe": "medium-term",
                        "confidence_score": 0.6,
                    })
                    break

            # Check for regular sell signals
            for pattern in sell_patterns:
                if re.search(pattern, text_lower) and symbol in text_upper:
                    signals.append({
                        "action": "SELL",
                        "symbol": symbol,
                        "entry_price": None,
                        "target_price": None,
                        "stop_loss": None,
                        "timeframe": "medium-term",
                        "confidence_score": 0.6,
                    })
                    break

            # Check for hold signals
            for pattern in hold_patterns:
                if re.search(pattern, text_lower) and symbol in text_upper:
                    signals.append({
                        "action": "HOLD",
                        "symbol": symbol,
                        "entry_price": None,
                        "target_price": None,
                        "stop_loss": None,
                        "timeframe": "medium-term",
                        "confidence_score": 0.3,
                    })
                    break

        # Remove duplicates
        unique_signals = []
        seen = set()
        for signal in signals:
            key = (signal["action"], signal["symbol"])
            if key not in seen:
                unique_signals.append(signal)
                seen.add(key)

        return unique_signals

    def _extract_price_targets(self, text: str, symbols: List[str]) -> Dict[str, Any]:
        """
        Extract price targets mentioned for symbols.

        Looks for patterns like $XXX.XX or numbers in typical price ranges.

        Args:
            text: Text to search
            symbols: List of symbols

        Returns:
            Dict mapping symbols to price targets
        """
        price_targets = {}

        # Pattern for prices: $123.45 or 123.45
        price_pattern = r'\$?(\d+\.?\d*)'

        # Look for price mentions near symbols
        for symbol in symbols:
            # Find mentions of symbol with nearby prices
            symbol_pattern = rf'{symbol}\s+[^.]*?(\$?(\d+(?:\.\d{{1,2}})?))(?:\s|$|[.,;])'
            matches = re.finditer(symbol_pattern, text, re.IGNORECASE)

            prices = []
            for match in matches:
                try:
                    price_str = match.group(1).replace('$', '')
                    price = float(price_str)
                    # Filter reasonable prices (between 0.01 and 100,000)
                    if 0.01 <= price <= 100000:
                        prices.append(price)
                except (ValueError, IndexError):
                    pass

            if prices:
                # Use average of found prices
                price_targets[symbol] = round(sum(prices) / len(prices), 2)

        return price_targets

    def _extract_insights(self, text: str) -> List[str]:
        """
        Extract market insights from text.

        Looks for sentences with keywords like trend, support, resistance, etc.

        Args:
            text: Text to search

        Returns:
            List of insight strings
        """
        insights = []
        insight_keywords = [
            'trend', 'support', 'resistance', 'breakout', 'breakdown',
            'reversal', 'consolidation', 'uptrend', 'downtrend',
            'bullish', 'bearish', 'momentum', 'overbought', 'oversold'
        ]

        # Split text into sentences
        sentences = re.split(r'[.!?]\s+', text)

        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in insight_keywords):
                cleaned = sentence.strip()
                if len(cleaned) > 20 and cleaned not in insights:
                    insights.append(cleaned[:150])  # Limit length

        return insights[:5]  # Return up to 5 insights

    def _generate_summary(self, text: str, signals: List[Dict], symbols: List[str]) -> str:
        """
        Generate basic summary from extracted content.

        Args:
            text: Original text
            signals: Extracted signals
            symbols: Extracted symbols

        Returns:
            Summary string
        """
        summary_parts = []

        # Add intro
        summary_parts.append("Report analysis summary:")

        # Add symbols mentioned
        if symbols:
            summary_parts.append(f"Symbols mentioned: {', '.join(symbols[:5])}")

        # Add signals
        if signals:
            buy_signals = [s for s in signals if s["action"] == "BUY"]
            sell_signals = [s for s in signals if s["action"] == "SELL"]
            if buy_signals:
                summary_parts.append(f"Buy signals identified: {', '.join([s['symbol'] for s in buy_signals])}")
            if sell_signals:
                summary_parts.append(f"Sell signals identified: {', '.join([s['symbol'] for s in sell_signals])}")

        # Add first 300 characters of content as context
        content_snippet = text[:200].replace('\n', ' ').strip()
        summary_parts.append(f"Content: {content_snippet}...")

        return '. '.join(summary_parts)
