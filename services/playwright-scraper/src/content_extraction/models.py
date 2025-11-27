"""Data models for content extraction."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class ExtractionResult:
    """Result of content extraction operation."""

    success: bool
    """Whether extraction completed successfully."""

    extracted_text: Optional[str] = None
    """Clean semantic HTML or plain text fallback."""

    extracted_images: List[Dict[str, Any]] = field(default_factory=list)
    """Image metadata JSONB array with base64 data."""

    author: Optional[str] = None
    """Extracted author name."""

    publication_date: Optional[datetime] = None
    """Parsed publication date in UTC."""

    title: Optional[str] = None
    """Article title."""

    fallback_used: Optional[str] = None
    """None | 'plain_text' | 'raw_html' - which fallback was used."""

    error_message: Optional[str] = None
    """Error details if extraction failed."""

    duration_ms: int = 0
    """Total extraction time in milliseconds."""

    images_downloaded: int = 0
    """Count of successfully downloaded images."""

    images_failed: int = 0
    """Count of failed image downloads."""
