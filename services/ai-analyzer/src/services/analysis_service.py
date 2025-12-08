"""
Analysis service orchestration layer.

Coordinates LLM analysis, database persistence, and error handling.
Manages the complete workflow from analysis request to stored response.
"""

import time
from src.llm.analyzer import LLMAnalyzer
from src.db.analyses_repository import AnalysesRepository
from src.utils.logger import get_logger
from src.models import AnalysisSuccessResponse
from src.config import get_config

logger = get_logger(__name__)


class AnalysisService:
    """Service orchestrating analysis workflow."""

    def __init__(self):
        """Initialize analysis service with dependencies."""
        self.llm_analyzer = LLMAnalyzer()
        self.analyses_repository = AnalysesRepository()
        self.config = get_config()

    async def analyze(self, report_id: str, raw_extracted_text: str, prompt_type: str = None, ai_provider: str = None, model_name: str = None, title: str = None) -> AnalysisSuccessResponse:
        """
        Analyze trading report with LLM.

        Workflow:
        1. Log analysis start
        2. Call LLM analyzer with optional prompt_type override
        3. Store raw response in database
        4. Return structured response

        Args:
            report_id: Report UUID
            raw_extracted_text: Raw text to analyze
            prompt_type: Optional prompt type override ('default', 'custom', 'options', etc.)
            ai_provider: Optional provider override
            model_name: Optional model name override
            title: Optional report title

        Returns:
            AnalysisSuccessResponse with analysis results

        Raises:
            Exception: On fatal errors
        """
        start_time = time.time()
        
        # Resolve prompt type from config if not provided
        effective_prompt_type = prompt_type or self.config.prompt_type

        logger.info(
            "Analysis request received",
            extra={
                "report_id": report_id,
                "content_length": len(raw_extracted_text),
                "prompt_type": effective_prompt_type,
                "ai_provider": ai_provider,
                "model_name": model_name,
                "title": title,
            }
        )

        # Default values for failure case
        api_provider = ai_provider or "unknown"
        raw_response = "Analysis failed."
        thinking_budget_tokens = None
        thinking_tokens_used = None
        thinking_content = None
        operations_found = False
        input_tokens = None
        output_tokens = None
        
        try:
            # Try LLM analysis (with optional prompt_type override)
            analysis_result = await self.llm_analyzer.analyze(
                raw_extracted_text, 
                report_id, 
                prompt_type=effective_prompt_type,
                ai_provider=ai_provider,
                model_name=model_name
            )

            if analysis_result:
                api_provider = analysis_result.get("api_provider", "unknown")
                
                if "error" in analysis_result:
                    # Handle error returned by LLM Analyzer
                    error_msg = analysis_result["error"]
                    logger.error(f"LLM Analysis returned error: {error_msg}")
                    raw_response = f"Analysis failed: {error_msg}"
                else:
                    # Successful analysis
                    raw_response = analysis_result.get("response", "")
                    thinking_budget_tokens = analysis_result.get("thinking_budget_tokens")
                    thinking_tokens_used = analysis_result.get("thinking_tokens_used")
                    thinking_content = analysis_result.get("thinking_content")
                    operations_found = analysis_result.get("operations_found", False)
                    model_name = analysis_result.get("model_name")
                    input_tokens = analysis_result.get("input_tokens")
                    output_tokens = analysis_result.get("output_tokens")
            else:
                logger.error("LLM Analysis returned None")
                raw_response = "Analysis failed: LLM provider returned no result."

        except Exception as e:
            logger.error(f"LLM Analysis failed with exception: {str(e)}")
            raw_response = f"Analysis failed: {str(e)}"

        # Store in database (raw response + metadata) - even if failed
        db_result = await self.analyses_repository.create_analysis(
            report_id=report_id,
            ai_provider=api_provider,
            raw_response=raw_response,
            thinking_budget_tokens=thinking_budget_tokens,
            thinking_tokens_used=thinking_tokens_used,
            thinking_content=thinking_content,
            operations_found=operations_found,
            model_used=model_name,
            prompt_type=effective_prompt_type,
            title=title,
            extracted_text=raw_extracted_text,
        )

        # Extract analysis ID from database result
        analysis_id = db_result.get("id", "")

        # Calculate response duration
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Analysis completed (potentially with errors)",
            extra={
                "analysis_id": analysis_id,
                "report_id": report_id,
                "provider": api_provider,
                "duration_ms": duration_ms,
                "thinking_tokens_used": thinking_tokens_used,
                "operations_found": operations_found,
            }
        )

        # Build response with raw markdown + metadata
        return AnalysisSuccessResponse(
            analysis_id=analysis_id,
            report_id=report_id,
            api_provider=api_provider,
            raw_analysis=raw_response,  # Main response - raw markdown from LLM
            thinking_budget_tokens=thinking_budget_tokens,
            thinking_tokens_used=thinking_tokens_used,
            thinking_content=thinking_content,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_latency_ms=duration_ms,
        )
