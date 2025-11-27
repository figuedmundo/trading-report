"""Main content extraction service."""

import logging
import time
import asyncio
import traceback
from typing import Optional, Tuple, List, Dict, Any
from bs4 import BeautifulSoup
import re

from src.content_extraction.config import ExtractionConfig
from src.content_extraction.models import ExtractionResult
from src.content_extraction.html_parser import (
    extract_semantic_html,
    extract_with_fallback,
    extract_element_text,
    extract_article_content,
)
from src.content_extraction.date_parser import parse_spanish_date
from src.content_extraction.image_handler import (
    download_images_parallel,
    resolve_relative_url,
)
from src.content_extraction.logging_utils import (
    log_extraction_completed,
    log_extraction_failed,
    log_metadata_extraction_failed,
)

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Extract clean content from trading report HTML."""

    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        Initialize content extractor.

        Args:
            config: Extraction configuration (uses default if None)
        """
        self.config = config or ExtractionConfig()

    async def extract_from_html(
        self,
        html: str,
        report_url: str,
        page_base_url: str,
        correlation_id: str,
        db_pool=None,
        report_id: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract clean content from HTML with cascading fallbacks.

        Args:
            html: Raw HTML content from page
            report_url: Original report URL
            page_base_url: Base URL for relative link resolution
            correlation_id: Request correlation ID for distributed tracing
            db_pool: Database connection pool for logging
            report_id: Report ID for logging

        Returns:
            ExtractionResult with extracted content or fallback
        """
        start_time = time.time()

        try:
            # Validate input
            if not html or not isinstance(html, str):
                return ExtractionResult(
                    success=False,
                    error_message="Invalid HTML input",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Extract article content
            article_html = extract_article_content(html, self.config)
            if not article_html:
                return ExtractionResult(
                    success=False,
                    error_message="Could not extract article content",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Extract metadata
            author = extract_element_text(html, self.config.author_selector)
            if not author and report_id:
                log_metadata_extraction_failed(
                    correlation_id, report_id, "author", db_pool
                )

            # Extract and parse date
            date_string = extract_element_text(html, self.config.date_selector)
            publication_date = None
            if date_string:
                publication_date = parse_spanish_date(date_string)
                if not publication_date and report_id:
                    log_metadata_extraction_failed(
                        correlation_id, report_id, "publication_date", db_pool
                    )

            # Extract title
            title = extract_element_text(html, self.config.title_selector)
            if not title and report_id:
                log_metadata_extraction_failed(
                    correlation_id, report_id, "title", db_pool
                )

            # Extract content with fallback cascade
            extracted_text, fallback_used = extract_with_fallback(html, article_html)

            # Extract and process images
            images_metadata, extracted_images = await self._extract_and_process_images(
                article_html, page_base_url
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Count downloaded vs failed images
            images_downloaded = sum(
                1 for img in images_metadata
                if img.get("download_status") == "success"
            )
            images_failed = sum(
                1 for img in images_metadata
                if img.get("download_status") == "failed"
            )
            tradingview_images = sum(
                1 for img in images_metadata
                if img.get("is_tradingview")
            )

            # Log success
            if report_id:
                log_extraction_completed(
                    correlation_id,
                    report_id,
                    duration_ms,
                    len(images_metadata),
                    images_downloaded,
                    images_failed,
                    tradingview_images,
                    len(extracted_text or ""),
                    author is not None,
                    publication_date is not None,
                    fallback_used,
                    db_pool,
                )

            return ExtractionResult(
                success=True,
                extracted_text=extracted_text,
                extracted_images=images_metadata,
                author=author,
                publication_date=publication_date,
                title=title,
                fallback_used=fallback_used,
                duration_ms=duration_ms,
                images_downloaded=images_downloaded,
                images_failed=images_failed,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            stack_trace = traceback.format_exc()

            logger.error(f"Content extraction failed: {error_msg}")

            # Log failure
            if report_id:
                log_extraction_failed(
                    correlation_id, report_id, error_msg, None, stack_trace, db_pool
                )

            return ExtractionResult(
                success=False,
                error_message=error_msg,
                duration_ms=duration_ms,
            )

    async def _extract_and_process_images(
        self,
        article_html: str,
        page_base_url: str,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Extract and process images from article content.

        Downloads regular images, stores TradingView URLs as references,
        and replaces image URLs with local:// references.

        Args:
            article_html: Article HTML content
            page_base_url: Base URL for relative URL resolution

        Returns:
            Tuple of (image_metadata_list, modified_html_with_local_refs)
        """
        try:
            soup = BeautifulSoup(article_html, "html.parser")
            img_tags = soup.select(self.config.image_selector)

            if not img_tags:
                return ([], article_html)

            # Extract image URLs
            image_urls = []
            for img in img_tags:
                src = img.get("src")
                if src:
                    image_urls.append(src)

            if not image_urls:
                return ([], article_html)

            # Download images in parallel
            images_metadata = await download_images_parallel(
                image_urls,
                page_base_url,
                max_concurrent=self.config.max_parallel_images,
                config=self.config,
            )

            # Replace URLs in HTML with local references
            modified_html = article_html
            for img_tag, metadata in zip(img_tags, images_metadata):
                old_src = img_tag.get("src")
                new_src = metadata.get("url")

                if old_src and new_src and old_src in modified_html:
                    modified_html = modified_html.replace(
                        f'src="{old_src}"', f'src="{new_src}"'
                    )

            return (images_metadata, modified_html)

        except Exception as e:
            logger.error(f"Error extracting and processing images: {e}")
            return ([], article_html)


async def extract_trading_report(
    html: str,
    report_url: str,
    page_base_url: str,
    correlation_id: str,
    db_pool=None,
    report_id: Optional[str] = None,
) -> ExtractionResult:
    """
    Public API for extracting trading report content.

    Args:
        html: Raw HTML from page
        report_url: Report URL
        page_base_url: Page base URL
        correlation_id: Request correlation ID
        db_pool: Database connection pool
        report_id: Report ID for logging

    Returns:
        ExtractionResult
    """
    extractor = ContentExtractor()
    return await extractor.extract_from_html(
        html, report_url, page_base_url, correlation_id, db_pool, report_id
    )
