"""
Analysis service orchestration layer.

Coordinates LLM analysis, fallback extraction, database persistence, and error handling.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
from src.llm.analyzer import LLMAnalyzer
from src.extraction.fallback import FallbackExtractor
from src.extraction.confidence import ConfidenceScorer
from src.db.analyses_repository import AnalysesRepository
from src.utils.logger import get_logger
from src.models import AnalysisSuccessResponse, TradingSignal

logger = get_logger(__name__)


class AnalysisService:
    """Service orchestrating analysis workflow."""

    def __init__(self):
        """Initialize analysis service with dependencies."""
        self.llm_analyzer = LLMAnalyzer()
        self.fallback_extractor = FallbackExtractor()
        self.confidence_scorer = ConfidenceScorer()
        self.analyses_repository = AnalysesRepository()

    async def analyze(self, report_id: str, raw_extracted_text: str) -> AnalysisSuccessResponse:
        """
        Analyze trading report with LLM and fallback extraction.

        Workflow:
        1. Log analysis start
        2. Call LLM analyzer
        3. On LLM failure: call fallback extractor
        4. Apply confidence scoring
        5. Store in database
        6. Return structured response

        Args:
            report_id: Report UUID
            raw_extracted_text: Raw text to analyze

        Returns:
            AnalysisSuccessResponse with analysis results

        Raises:
            Exception: On fatal errors (no LLM + fallback both failed)
        """
        start_time = datetime.now(timezone.utc)

        logger.info(
            "Analysis request received",
            extra={
                "report_id": report_id,
                "content_length": len(raw_extracted_text),
            }
        )

        # Try LLM analysis first
        analysis_result = await self.llm_analyzer.analyze(raw_extracted_text, report_id)

        # If LLM failed, use fallback extraction
        if analysis_result is None:
            logger.warning(
                "LLM analysis failed, using fallback extraction",
                extra={"report_id": report_id}
            )
            analysis_result = self.fallback_extractor.extract_analysis(raw_extracted_text)

        # Get provider name
        api_provider = analysis_result.get("api_provider", "fallback_keyword")

        # Apply confidence scoring to signals
        trading_signals = analysis_result.get("trading_signals", [])
        scored_signals = self.confidence_scorer.score_signals(trading_signals, raw_extracted_text)
        analysis_result["trading_signals"] = scored_signals

        # Ensure all required fields are present and properly typed
        summary = analysis_result.get("summary", "")
        market_insights = analysis_result.get("market_insights", [])
        symbols_mentioned = analysis_result.get("symbols_mentioned", [])
        price_targets = analysis_result.get("price_targets", {})

        # Validate arrays are never null
        if not isinstance(market_insights, list):
            market_insights = []
        if not isinstance(symbols_mentioned, list):
            symbols_mentioned = []
        if not isinstance(price_targets, dict):
            price_targets = {}

        # Store in database
        stored_analysis = await self.analyses_repository.create_analysis(
            report_id=report_id,
            summary=summary,
            trading_signals=scored_signals,
            ai_provider=api_provider,
        )

        # Calculate response duration
        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        logger.info(
            "Analysis completed successfully",
            extra={
                "report_id": report_id,
                "provider": api_provider,
                "duration_ms": duration_ms,
                "signal_count": len(scored_signals),
            }
        )

        # Build response with TradingSignal models
        signal_models = [
            TradingSignal(**signal) for signal in scored_signals
        ]

        return AnalysisSuccessResponse(
            report_id=report_id,
            api_provider=api_provider,
            summary=summary,
            trading_signals=signal_models,
            market_insights=market_insights,
            symbols_mentioned=symbols_mentioned,
            price_targets=price_targets,
            raw_extracted_text=raw_extracted_text,
        )
