"""
Tests for LLM integration module.

Tests LLM analysis and fallback extraction functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.llm.analyzer import LLMAnalyzer
from src.extraction.fallback import FallbackExtractor
from src.extraction.confidence import ConfidenceScorer


@pytest.fixture
def sample_report_text():
    """Sample trading report text for testing."""
    return """
    Trading Report Analysis

    BTC (Bitcoin) is showing strong buy signals with price target of 45000.
    The uptrend is confirmed at support level 40000.

    ETH (Ethereum) recommendation: Sell with stop loss at 2500.

    SPY - Hold position, waiting for breakout above 460.

    Market insights: Strong momentum in crypto markets, resistance forming at 450.
    """


@pytest.fixture
def sample_llm_response():
    """Sample LLM response."""
    return {
        "summary": "Strong buy signals for BTC with target 45000. ETH showing sell signal. SPY in consolidation.",
        "trading_signals": [
            {
                "action": "BUY",
                "symbol": "BTC",
                "entry_price": 43000.0,
                "target_price": 45000.0,
                "stop_loss": 40000.0,
                "timeframe": "medium-term",
                "confidence_score": 0.9,
            },
            {
                "action": "SELL",
                "symbol": "ETH",
                "entry_price": 2800.0,
                "target_price": 2500.0,
                "stop_loss": None,
                "timeframe": "short-term",
                "confidence_score": 0.6,
            },
        ],
        "market_insights": [
            "Strong momentum in crypto markets",
            "Resistance forming at 450 level",
        ],
        "symbols_mentioned": ["BTC", "ETH", "SPY"],
        "price_targets": {"BTC": 45000.0, "ETH": 2500.0},
        "api_provider": "anthropic",
    }


@pytest.mark.asyncio
async def test_llm_analyzer_successful_analysis(sample_report_text, sample_llm_response):
    """Test successful LLM analysis."""
    with patch('src.llm.analyzer.get_llm_provider') as mock_provider_factory:
        # Mock LLM provider
        mock_provider = MagicMock()
        mock_provider.get_provider_name.return_value = "anthropic"
        mock_provider.analyze = AsyncMock(return_value=sample_llm_response)
        mock_provider_factory.return_value = mock_provider

        # Test analyzer
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze(sample_report_text, "test-report-123")

        # Verify result
        assert result is not None
        assert result["api_provider"] == "anthropic"
        assert len(result["trading_signals"]) == 2
        assert result["trading_signals"][0]["action"] == "BUY"
        assert result["trading_signals"][0]["symbol"] == "BTC"
        assert result["summary"] is not None


@pytest.mark.asyncio
async def test_fallback_extraction_on_llm_failure(sample_report_text):
    """Test fallback extraction triggered on LLM failure."""
    with patch('src.llm.analyzer.get_llm_provider') as mock_provider_factory:
        # Mock LLM provider to simulate failure
        mock_provider = MagicMock()
        mock_provider.get_provider_name.return_value = "anthropic"
        mock_provider.analyze = AsyncMock(side_effect=Exception("API Error"))
        mock_provider_factory.return_value = mock_provider

        # Test analyzer
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze(sample_report_text, "test-report-123")

        # Fallback returns None, should trigger fallback extraction in service
        assert result is None


@pytest.mark.asyncio
async def test_llm_analyzer_timeout():
    """Test LLM analyzer timeout behavior."""
    with patch('src.llm.analyzer.get_llm_provider') as mock_provider_factory:
        # Mock LLM provider to simulate timeout
        async def slow_analyze(*args, **kwargs):
            await asyncio.sleep(2)  # Sleep longer than timeout
            return {"summary": "test"}

        mock_provider = MagicMock()
        mock_provider.get_provider_name.return_value = "anthropic"
        mock_provider.analyze = slow_analyze
        mock_provider_factory.return_value = mock_provider

        with patch('src.llm.analyzer.get_config') as mock_config:
            # Set very short timeout
            mock_cfg = MagicMock()
            mock_cfg.analysis_timeout = 0.1
            mock_config.return_value = mock_cfg

            analyzer = LLMAnalyzer()
            result = await analyzer.analyze("test content", "test-report-123")

            # Should return None on timeout
            assert result is None


def test_fallback_extractor_extract_symbols(sample_report_text):
    """Test symbol extraction from fallback."""
    extractor = FallbackExtractor()
    symbols = extractor._extract_symbols(sample_report_text)

    assert "BTC" in symbols
    assert "ETH" in symbols
    assert "SPY" in symbols


def test_fallback_extractor_extract_price_targets(sample_report_text):
    """Test price target extraction."""
    extractor = FallbackExtractor()
    price_targets = extractor._extract_price_targets(sample_report_text, ["BTC", "ETH"])

    assert "BTC" in price_targets
    assert price_targets["BTC"] == 45000.0
    assert "ETH" in price_targets
    assert price_targets["ETH"] == 2500.0


def test_fallback_extractor_full_analysis(sample_report_text):
    """Test full fallback extraction."""
    extractor = FallbackExtractor()
    result = extractor.extract_analysis(sample_report_text)

    assert result["api_provider"] == "fallback_keyword"
    assert len(result["symbols_mentioned"]) > 0
    assert result["summary"] is not None
    assert isinstance(result["trading_signals"], list)
    assert isinstance(result["market_insights"], list)
    assert isinstance(result["price_targets"], dict)


def test_confidence_scorer_explicit_signal():
    """Test confidence scoring for explicit signals."""
    scorer = ConfidenceScorer()
    signal = {
        "action": "BUY",
        "symbol": "AAPL",
        "confidence_score": None,
    }
    text = "We strongly recommend buying AAPL at current levels."

    scored = scorer.score_signal(signal, text)
    assert scored["confidence_score"] == 0.9


def test_confidence_scorer_implied_signal():
    """Test confidence scoring for implied signals."""
    scorer = ConfidenceScorer()
    signal = {
        "action": "BUY",
        "symbol": "MSFT",
        "confidence_score": None,
    }
    text = "MSFT is in a strong uptrend with support at 350."

    scored = scorer.score_signal(signal, text)
    assert scored["confidence_score"] == 0.6


def test_confidence_scorer_passing_mention():
    """Test confidence scoring for passing mention."""
    scorer = ConfidenceScorer()
    signal = {
        "action": "HOLD",
        "symbol": "GOOGL",
        "confidence_score": None,
    }
    text = "The report mentions GOOGL and suggests to hold."

    scored = scorer.score_signal(signal, text)
    assert scored["confidence_score"] == 0.3
