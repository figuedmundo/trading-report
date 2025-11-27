"""Image downloading and handling for content extraction."""

import logging
import base64
import asyncio
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin
import httpx
from src.content_extraction.config import ExtractionConfig

logger = logging.getLogger(__name__)


def is_tradingview_image(url: str, config: Optional[ExtractionConfig] = None) -> bool:
    """
    Check if image is hosted on TradingView CDN.

    Args:
        url: Image URL
        config: Extraction configuration

    Returns:
        True if URL matches TradingView patterns, False otherwise
    """
    if not url:
        return False

    config = config or ExtractionConfig()
    url_lower = url.lower()

    return any(pattern in url_lower for pattern in config.tradingview_patterns)


def validate_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL to validate

    Returns:
        True if valid http/https URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    return url.startswith("http://") or url.startswith("https://")


def resolve_relative_url(relative_url: str, base_url: str) -> str:
    """
    Convert relative URL to absolute URL.

    Args:
        relative_url: Relative or absolute URL
        base_url: Base URL for resolution

    Returns:
        Absolute URL
    """
    if not relative_url or not base_url:
        return relative_url

    return urljoin(base_url, relative_url)


async def download_image_with_retry(
    url: str,
    timeout: int = 10,
    max_retries: int = 2
) -> Optional[bytes]:
    """
    Download image with retry logic.

    Retries on timeout/connection errors with exponential backoff.
    Skips retries for permanent HTTP errors (404, 403).

    Args:
        url: Image URL
        timeout: Timeout per request in seconds
        max_retries: Maximum retry attempts

    Returns:
        Image bytes or None on failure
    """
    if not url or not validate_url(url):
        logger.warning(f"Invalid image URL: {url}")
        return None

    retries = 0
    backoff_delays = [1, 2]  # Exponential backoff: 1s, 2s

    while retries <= max_retries:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)

                # Check for HTTP errors
                if response.status_code == 404 or response.status_code == 403:
                    logger.warning(f"Image not found or forbidden: {url} (HTTP {response.status_code})")
                    return None

                if response.status_code != 200:
                    logger.warning(f"HTTP error downloading image: {url} (HTTP {response.status_code})")
                    if retries < max_retries:
                        await asyncio.sleep(backoff_delays[min(retries, len(backoff_delays) - 1)])
                        retries += 1
                        continue
                    return None

                # Validate image size
                content_length = response.headers.get("content-length")
                if content_length:
                    size_bytes = int(content_length)
                    if size_bytes > 5 * 1024 * 1024:  # 5MB limit
                        logger.warning(f"Image too large: {url} ({size_bytes} bytes)")
                        return None

                return response.content

        except (asyncio.TimeoutError, httpx.TimeoutException) as e:
            logger.debug(f"Timeout downloading image (attempt {retries + 1}): {url}")
            if retries < max_retries:
                await asyncio.sleep(backoff_delays[min(retries, len(backoff_delays) - 1)])
                retries += 1
                continue
            logger.warning(f"Failed to download image after {max_retries} retries: {url}")
            return None

        except Exception as e:
            logger.warning(f"Error downloading image: {url}: {e}")
            if retries < max_retries:
                await asyncio.sleep(backoff_delays[min(retries, len(backoff_delays) - 1)])
                retries += 1
                continue
            return None

    return None


def encode_image_to_base64(image_bytes: bytes) -> Optional[str]:
    """
    Encode image bytes to base64 string.

    Args:
        image_bytes: Binary image data

    Returns:
        Base64 encoded string or None if invalid
    """
    if not image_bytes or len(image_bytes) < 100:
        logger.warning(f"Image too small or invalid: {len(image_bytes) if image_bytes else 0} bytes")
        return None

    try:
        return base64.b64encode(image_bytes).decode("utf-8")
    except Exception as e:
        logger.error(f"Error encoding image to base64: {e}")
        return None


def build_image_metadata(
    url: str,
    content_type: str,
    position_index: int,
    base64_data: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    is_tradingview: bool = False,
    download_status: str = "success"
) -> Dict[str, Any]:
    """
    Build JSONB-compatible image metadata dict.

    Args:
        url: Image URL
        content_type: MIME type
        position_index: Sequential order in article
        base64_data: Base64 encoded image data (non-TradingView only)
        width: Image width in pixels
        height: Image height in pixels
        is_tradingview: TradingView image flag
        download_status: "success" | "failed" | "tradingview_link"

    Returns:
        Image metadata dict
    """
    metadata = {
        "url": url,
        "content_type": content_type,
        "position_index": position_index,
        "is_tradingview": is_tradingview,
        "download_status": download_status,
    }

    if base64_data:
        metadata["base64_data"] = base64_data

    if width is not None:
        metadata["width"] = width

    if height is not None:
        metadata["height"] = height

    return metadata


async def download_images_parallel(
    image_urls: List[str],
    page_base_url: str,
    max_concurrent: int = 3,
    config: Optional[ExtractionConfig] = None
) -> List[Dict[str, Any]]:
    """
    Download multiple images in parallel with concurrency limit.

    Args:
        image_urls: List of image URLs to download
        page_base_url: Base URL for resolving relative URLs
        max_concurrent: Maximum concurrent downloads
        config: Extraction configuration

    Returns:
        List of image metadata dicts in same order as input
    """
    if not image_urls:
        return []

    config = config or ExtractionConfig()
    semaphore = asyncio.Semaphore(max_concurrent)

    async def download_single(url: str, index: int) -> Dict[str, Any]:
        """Download single image with semaphore."""
        async with semaphore:
            # Resolve relative URL to absolute
            absolute_url = resolve_relative_url(url, page_base_url)

            # Check if TradingView image
            if is_tradingview_image(absolute_url, config):
                logger.debug(f"Skipping TradingView image: {absolute_url}")
                return build_image_metadata(
                    url=absolute_url,
                    content_type="text/html",
                    position_index=index,
                    is_tradingview=True,
                    download_status="tradingview_link"
                )

            # Download image
            logger.debug(f"Downloading image: {absolute_url}")
            image_bytes = await download_image_with_retry(
                absolute_url,
                timeout=config.image_download_timeout_s,
                max_retries=config.image_download_retries
            )

            if image_bytes:
                # Encode to base64
                base64_data = encode_image_to_base64(image_bytes)

                if base64_data:
                    logger.debug(f"Successfully downloaded image: {absolute_url}")
                    return build_image_metadata(
                        url=f"local://image-{index}",
                        content_type="image/unknown",  # Could be enhanced with magic bytes
                        position_index=index,
                        base64_data=base64_data,
                        is_tradingview=False,
                        download_status="success"
                    )
                else:
                    logger.warning(f"Failed to encode image to base64: {absolute_url}")
                    return build_image_metadata(
                        url=absolute_url,
                        content_type="image/unknown",
                        position_index=index,
                        is_tradingview=False,
                        download_status="failed"
                    )
            else:
                logger.warning(f"Failed to download image: {absolute_url}")
                return build_image_metadata(
                    url=absolute_url,
                    content_type="image/unknown",
                    position_index=index,
                    is_tradingview=False,
                    download_status="failed"
                )

    # Download all images concurrently
    try:
        results = await asyncio.gather(*[
            download_single(url, i) for i, url in enumerate(image_urls)
        ])
        return results
    except Exception as e:
        logger.error(f"Error downloading images in parallel: {e}")
        # Return placeholder metadata for all images
        return [
            build_image_metadata(
                url=url,
                content_type="image/unknown",
                position_index=i,
                is_tradingview=False,
                download_status="failed"
            )
            for i, url in enumerate(image_urls)
        ]
