"""
API route handlers for scraper service.

Defines POST /api/v1/scrape and GET /health endpoints.
"""

import uuid
from datetime import datetime, timezone
from typing import Union

from fastapi import APIRouter, HTTPException
from src.config import Config
from src.models import (
    ScrapeRequest,
    ScrapeSuccessResponse,
    ScrapeErrorResponse,
    HealthCheckResponse,
    ImageData,
)
from src.browser import BrowserManager
from src.extractor import ContentExtractor
from src.utils.image_handler import ImageHandler
from src.utils.screenshot import capture_screenshot
from src.utils.logger import get_logger
from src.utils.exceptions import (
    LoginError,
    NavigationError,
    ExtractionError,
    CredentialError,
)

logger = get_logger(__name__)

router = APIRouter()


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
        "browser_version": "1.40.0",
        "extraction_duration_ms": duration_ms,
        "request_id": request_id,
    }


@router.post("/api/v1/scrape", response_model=Union[ScrapeSuccessResponse, ScrapeErrorResponse])
async def scrape_endpoint(request: ScrapeRequest) -> Union[ScrapeSuccessResponse, ScrapeErrorResponse]:
    """
    Scrape trading report from portal.

    Args:
        request: ScrapeRequest with url and optional credentials

    Returns:
        ScrapeSuccessResponse or ScrapeErrorResponse
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)
    url_str = str(request.url)

    logger.info(f"Scrape request received", extra={"url": url_str, "request_id": request_id})

    config = Config()
    browser_manager = BrowserManager(config)

    try:
        # Launch browser
        async with browser_manager as manager:
            # Navigate to login page
            logger.info("Navigating to login page")
            await manager.page.goto(
                config.login_url,
                wait_until="networkidle",
                timeout=config.login_timeout * 1000,
            )

            # Check if login required and perform login
            if await manager.needs_login():
                logger.info("Login required, performing authentication")
                # Use request credentials if provided, otherwise use environment variables (secure default)
                username = request.username or config.trading_portal_username
                password = request.password or config.trading_portal_password

                if not username or not password:
                    raise CredentialError("No credentials available (set TRADING_PORTAL_USERNAME and TRADING_PORTAL_PASSWORD in .env)")

                await manager.login(username, password)
            else:
                logger.info("Login not required")

            # Extract content
            extractor = ContentExtractor(config)
            content = await extractor.extract_content(manager.page, url_str)

            # Extract images
            image_handler = ImageHandler(config)
            images = image_handler.extract_image_urls(content["html_content"])
            tradingview_images = image_handler.filter_tradingview_urls(images)
            downloaded_images = await image_handler.download_images(tradingview_images)

            # Create ImageData objects
            image_data_objects = [
                ImageData(
                    url=img["url"],
                    base64=img["base64"],
                    width=img.get("width"),
                    height=img.get("height"),
                )
                for img in downloaded_images
            ]

            # Capture screenshot
            screenshot = await capture_screenshot(manager.page, config)

            # Build success response
            logger.info(f"Scrape completed successfully for {url_str}")

            return ScrapeSuccessResponse(
                success=True,
                url=url_str,
                title=content["title"],
                html_content=content["html_content"],
                text_content=content["text_content"],
                report_images=image_data_objects,
                screenshot_base64=screenshot,
                metadata=_create_metadata(request_id, start_time),
            )

    except CredentialError as e:
        logger.error(f"Credential error: {e.message}", extra={"url": url_str, "request_id": request_id})
        return ScrapeErrorResponse(
            success=False,
            url=url_str,
            error=e.message,
            error_type="CredentialError",
            metadata=_create_metadata(request_id, start_time),
        )

    except LoginError as e:
        logger.error(f"Login error: {e.message}", extra={"url": url_str, "request_id": request_id})
        return ScrapeErrorResponse(
            success=False,
            url=url_str,
            error=e.message,
            error_type="LoginError",
            metadata=_create_metadata(request_id, start_time),
        )

    except NavigationError as e:
        logger.error(f"Navigation error: {e.message}", extra={"url": url_str, "request_id": request_id})
        return ScrapeErrorResponse(
            success=False,
            url=url_str,
            error=e.message,
            error_type="NavigationError",
            metadata=_create_metadata(request_id, start_time),
        )

    except ExtractionError as e:
        logger.error(f"Extraction error: {e.message}", extra={"url": url_str, "request_id": request_id})
        return ScrapeErrorResponse(
            success=False,
            url=url_str,
            error=e.message,
            error_type="ExtractionError",
            metadata=_create_metadata(request_id, start_time),
        )

    except Exception as e:
        logger.error(f"Unexpected error during scrape: {e}", extra={"url": url_str, "request_id": request_id})
        return ScrapeErrorResponse(
            success=False,
            url=url_str,
            error=str(e),
            error_type="UnexpectedError",
            metadata=_create_metadata(request_id, start_time),
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
        service="playwright-scraper",
        version="0.1.0",
    )
