"""
Pydantic models for request and response validation.

Defines all input validation models and output response structures.
"""

from pydantic import BaseModel, field_validator, Field
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
    prompt_type: Optional[str] = None  # Optional: override default prompt with 'default', 'custom', 'options', etc.

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

    analysis_id: str  # UUID of analysis record in database
    report_id: str
    api_provider: str  # Any provider name: anthropic, groq, gemini, etc.

    # Main AI response (raw markdown as returned by LLM)
    raw_analysis: str  # Complete markdown response from LLM

    # Optional parsed fields (for backward compatibility / convenience)
    summary: Optional[str] = Field(default=None, description="Extracted summary if available")
    trading_signals: List[Dict] = Field(default_factory=list, description="Extracted trading signals if available")
    market_insights: List[str] = Field(default_factory=list, description="Extracted market insights if available")
    symbols_mentioned: List[str] = Field(default_factory=list, description="Extracted symbols if available")
    price_targets: Dict[str, Optional[float]] = Field(default_factory=dict, description="Extracted price targets if available")

    # Extended thinking metadata (optional)
    thinking_budget_tokens: Optional[int] = Field(default=None, description="Token budget allocated for extended thinking")
    thinking_tokens_used: Optional[int] = Field(default=None, description="Actual tokens consumed by thinking process")
    thinking_content: Optional[str] = Field(default=None, description="Full reasoning trace from extended thinking")

    # Provider and performance metadata
    model_name: Optional[str] = Field(default=None, description="LLM model name used for analysis")
    input_tokens: Optional[int] = Field(default=None, description="Input tokens used by LLM")
    output_tokens: Optional[int] = Field(default=None, description="Output tokens used by LLM")
    response_latency_ms: Optional[int] = Field(default=None, description="Total response time in milliseconds")


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
