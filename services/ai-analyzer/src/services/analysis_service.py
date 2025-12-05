"""
Analysis service orchestration layer.

Coordinates LLM analysis, fallback extraction, database persistence, and error handling.
Manages the complete workflow from analysis request to stored response.
"""

import time
from src.llm.analyzer import LLMAnalyzer
from src.extraction.fallback import FallbackExtractor
from src.extraction.confidence import ConfidenceScorer
from src.db.analyses_repository import AnalysesRepository
from src.utils.logger import get_logger
from src.models import AnalysisSuccessResponse

logger = get_logger(__name__)


class AnalysisService:
    """Service orchestrating analysis workflow."""

    def __init__(self):
        """Initialize analysis service with dependencies."""
        self.llm_analyzer = LLMAnalyzer()
        self.fallback_extractor = FallbackExtractor()
        self.confidence_scorer = ConfidenceScorer()
        self.analyses_repository = AnalysesRepository()

    async def analyze(self, report_id: str, raw_extracted_text: str, prompt_type: str = None) -> AnalysisSuccessResponse:
        """
        Analyze trading report with LLM and fallback extraction.

        Workflow:
        1. Log analysis start
        2. Call LLM analyzer with optional prompt_type override
        3. On LLM failure: call fallback extractor
        4. Store raw response in database
        5. Return structured response

        Args:
            report_id: Report UUID
            raw_extracted_text: Raw text to analyze
            prompt_type: Optional prompt type override ('default', 'custom', 'options', etc.)

        Returns:
            AnalysisSuccessResponse with analysis results

        Raises:
            Exception: On fatal errors (no LLM + fallback both failed)
        """
        start_time = time.time()

        logger.info(
            "Analysis request received",
            extra={
                "report_id": report_id,
                "content_length": len(raw_extracted_text),
            }
        )

        # Try LLM analysis first (with optional prompt_type override)
        analysis_result = await self.llm_analyzer.analyze(raw_extracted_text, report_id, prompt_type=prompt_type)

        # If LLM failed, use fallback extraction
        if analysis_result is None:
            logger.warning(
                "LLM analysis failed, using fallback extraction",
                extra={"report_id": report_id}
            )
            analysis_result = self.fallback_extractor.extract_analysis(raw_extracted_text)
            # Fallback doesn't produce thinking metadata
            analysis_result["thinking_tokens_used"] = None
            analysis_result["thinking_content"] = None
            analysis_result["operations_found"] = False
            # Fallback extraction still comes from LLM analyzer's provider attempt
            if "api_provider" not in analysis_result:
                # Use groq as default fallback provider (must be valid enum)
                analysis_result["api_provider"] = "groq"

        # Get provider name
        api_provider = analysis_result.get("api_provider", "groq")

        # Get raw response (most important - just the markdown as returned)
        raw_response = analysis_result.get("response", "")

        # Extract optional metadata if available
        trading_signals = analysis_result.get("trading_signals", [])
        market_insights = analysis_result.get("market_insights", [])
        symbols_mentioned = analysis_result.get("symbols_mentioned", [])
        price_targets = analysis_result.get("price_targets", {})
        summary = analysis_result.get("summary")

        # Apply confidence scoring to signals if available
        if trading_signals:
            scored_signals = self.confidence_scorer.score_signals(trading_signals, raw_extracted_text)
        else:
            scored_signals = []

        # Validate arrays are never null
        if not isinstance(market_insights, list):
            market_insights = []
        if not isinstance(symbols_mentioned, list):
            symbols_mentioned = []
        if not isinstance(price_targets, dict):
            price_targets = {}

        # Extract thinking metadata
        thinking_budget_tokens = analysis_result.get("thinking_budget_tokens")
        thinking_tokens_used = analysis_result.get("thinking_tokens_used")
        thinking_content = analysis_result.get("thinking_content")
        operations_found = analysis_result.get("operations_found", False)
        model_name = analysis_result.get("model_name")
        input_tokens = analysis_result.get("input_tokens")
        output_tokens = analysis_result.get("output_tokens")

        # Store in database (raw response + metadata)
        db_result = await self.analyses_repository.create_analysis(
            report_id=report_id,
            summary=summary or "",
            trading_signals=scored_signals,
            ai_provider=api_provider,
            raw_response=raw_response,
            thinking_budget_tokens=thinking_budget_tokens,
            thinking_tokens_used=thinking_tokens_used,
            thinking_content=thinking_content,
            operations_found=operations_found,
        )

        # Extract analysis ID from database result
        analysis_id = db_result.get("id", "")

        # Calculate response duration
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Analysis completed successfully",
            extra={
                "analysis_id": analysis_id,
                "report_id": report_id,
                "provider": api_provider,
                "duration_ms": duration_ms,
                "signal_count": len(scored_signals),
                "thinking_tokens_used": thinking_tokens_used,
                "operations_found": operations_found,
            }
        )

        # Build response with raw markdown + optional metadata
        return AnalysisSuccessResponse(
            analysis_id=analysis_id,
            report_id=report_id,
            api_provider=api_provider,
            raw_analysis=raw_response,  # Main response - raw markdown from LLM
            summary=summary,  # Optional: extracted summary
            trading_signals=scored_signals,  # Optional: extracted signals
            market_insights=market_insights,  # Optional: extracted insights
            symbols_mentioned=symbols_mentioned,  # Optional: extracted symbols
            price_targets=price_targets,  # Optional: extracted price targets
            thinking_budget_tokens=thinking_budget_tokens,
            thinking_tokens_used=thinking_tokens_used,
            thinking_content=thinking_content,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_latency_ms=duration_ms,
        )
