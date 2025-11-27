"""
Pydantic models for request and response validation.

Defines all input validation models and output response structures.
"""

from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List
from datetime import datetime


class ImageData(BaseModel):
    """Image object with base64 encoded data."""

    url: str
    base64: str
    width: Optional[int] = None
    height: Optional[int] = None


class ScrapeRequest(BaseModel):
    """Request body for POST /api/v1/scrape endpoint."""

    url: HttpUrl
    username: Optional[str] = None
    password: Optional[str] = None
    credential_id: Optional[str] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: HttpUrl) -> HttpUrl:
        """Validate that URL is a proper HTTP/HTTPS URL."""
        if not v.scheme or v.scheme not in ("http", "https"):
            raise ValueError("URL must use HTTP or HTTPS protocol")
        return v


class ScrapeSuccessResponse(BaseModel):
    """Success response body for scrape endpoint."""

    success: bool = True
    url: str
    title: str
    html_content: str
    text_content: str
    report_images: List[ImageData] = []
    screenshot_base64: str = ""
    metadata: dict


class ScrapeErrorResponse(BaseModel):
    """Error response body for scrape endpoint."""

    success: bool = False
    url: str
    error: str
    error_type: str
    html_content: str = ""
    text_content: str = ""
    report_images: List[ImageData] = []
    metadata: dict


class HealthCheckResponse(BaseModel):
    """Health check response body."""

    status: str
    service: str
    version: str
