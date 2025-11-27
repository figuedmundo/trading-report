"""
Pydantic models for request and response validation.

Defines all input validation models and output response structures.
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict


class TradingSignal(BaseModel):
    """Trading signal with action, symbol, prices, and confidence."""

    action: str  # BUY, SELL, HOLD
    symbol: str
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    timeframe: Optional[str] = None  # short-term, medium-term, long-term
    confidence_score: float  # 0.0 - 1.0


class AnalysisRequest(BaseModel):
    """Request body for POST /api/v1/analyze endpoint."""

    report_id: str
    raw_extracted_text: str

    @field_validator("report_id")
    @classmethod
    def validate_report_id(cls, v: str) -> str:
        """Validate that report_id is non-empty string."""
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("report_id must be a non-empty string")
        return v

    @field_validator("raw_extracted_text")
    @classmethod
    def validate_raw_text(cls, v: str) -> str:
        """Validate that raw_extracted_text is non-empty string."""
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("raw_extracted_text must be a non-empty string")
        return v


class AnalysisSuccessResponse(BaseModel):
    """Success response body for analysis endpoint."""

    report_id: str
    api_provider: str  # anthropic, groq, or fallback_keyword
    summary: str
    trading_signals: List[TradingSignal] = []
    market_insights: List[str] = []
    symbols_mentioned: List[str] = []
    price_targets: Dict[str, Optional[float]] = {}
    raw_extracted_text: str


class AnalysisErrorResponse(BaseModel):
    """Error response body for analysis endpoint."""

    report_id: str
    error: str
    error_type: str
    api_provider: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response body."""

    status: str
    service: str
    version: str
