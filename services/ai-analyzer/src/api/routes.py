"""
API route handlers for analysis service.

Defines POST /api/v1/analyze and GET /health endpoints.
"""

import uuid
from datetime import datetime, timezone
from typing import Union, Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import ValidationError

from src.models import (
    AnalysisRequest,
    AnalysisSuccessResponse,
    AnalysisErrorResponse,
    HealthCheckResponse,
)
from src.services.analysis_service import AnalysisService
from src.utils.logger import get_logger
from src.utils.exceptions import AnalysisError

logger = get_logger(__name__)

router = APIRouter()

# Analysis service instance (will be set during app initialization)
_analysis_service: AnalysisService = None


def set_analysis_service(service: AnalysisService) -> None:
    """Set analysis service instance."""
    global _analysis_service
    _analysis_service = service


def _create_metadata(request_id: str, start_time: datetime) -> dict:
    """
    Create response metadata.

    Args:
        request_id: Request UUID
        start_time: Request start time

    Returns:
        Metadata dict
    """
    duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "request_id": request_id,
    }


@router.post("/api/v1/analyze", response_model=Union[AnalysisSuccessResponse, AnalysisErrorResponse])
async def analyze_endpoint(
    request: AnalysisRequest,
    x_ai_provider: Optional[str] = Header(None, alias="X-AI-Provider"),
    x_llm_model: Optional[str] = Header(None, alias="X-LLM-Model"),
    x_prompt_name: Optional[str] = Header(None, alias="X-Prompt-Name"),
) -> Union[AnalysisSuccessResponse, AnalysisErrorResponse]:
    """
    Analyze trading report and extract signals.

    Args:
        request: AnalysisRequest with report_id and raw_extracted_text
        x_ai_provider: Optional header to override AI provider
        x_llm_model: Optional header to override LLM model
        x_prompt_name: Optional header to override prompt type

    Returns:
        AnalysisSuccessResponse or AnalysisErrorResponse
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    logger.info(
        "Analysis endpoint called",
        extra={
            "request_id": request_id,
            "report_id": request.report_id,
            "headers": {
                "ai_provider": x_ai_provider,
                "llm_model": x_llm_model,
                "prompt_name": x_prompt_name,
            }
        }
    )

    try:
        # Validate input
        if not request.report_id or not request.report_id.strip():
            logger.warning(
                "Invalid report_id in request",
                extra={"request_id": request_id}
            )
            raise HTTPException(
                status_code=400,
                detail="report_id must be non-empty string"
            )

        if not request.raw_extracted_text or not request.raw_extracted_text.strip():
            logger.warning(
                "Invalid raw_extracted_text in request",
                extra={"request_id": request_id, "report_id": request.report_id}
            )
            raise HTTPException(
                status_code=400,
                detail="raw_extracted_text must be non-empty string"
            )

        # Get or initialize service
        service = _analysis_service
        if service is None:
            service = AnalysisService()

        # Determine effective prompt type: Header overrides Body
        effective_prompt_type = x_prompt_name if x_prompt_name else request.prompt_type

        # Call analysis service with optional overrides
        response = await service.analyze(
            request.report_id,
            request.raw_extracted_text,
            prompt_type=effective_prompt_type,
            ai_provider=x_ai_provider,
            model_name=x_llm_model
        )

        logger.info(
            "Analysis completed successfully",
            extra={
                "request_id": request_id,
                "report_id": request.report_id,
                "provider": response.api_provider,
                "duration_ms": (datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
            }
        )

        return response

    except ValidationError as e:
        logger.error(
            f"Request validation error: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
            }
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid request body"
        )

    except AnalysisError as e:
        logger.error(
            f"Analysis error: {e.message}",
            extra={
                "request_id": request_id,
                "report_id": request.report_id,
                "error_code": e.error_code,
            }
        )
        raise HTTPException(
            status_code=500,
            detail=e.message
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(
            f"Unexpected error during analysis: {str(e)}",
            extra={
                "request_id": request_id,
                "report_id": request.report_id if hasattr(request, 'report_id') else "unknown",
                "error": str(e),
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during analysis"
        )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns:
        HealthCheckResponse with status ok
    """
    return HealthCheckResponse(
        status="ok",
        service="ai-analyzer",
        version="0.1.0",
    )
