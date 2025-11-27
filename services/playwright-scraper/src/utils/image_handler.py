"""
Image extraction and download handling.

Downloads images from URLs and encodes them as base64.
"""

import base64
import re
import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import aiohttp
from src.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ImageHandler:
    """Handles image extraction, download, and encoding."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize image handler.

        Args:
            config: Config instance (uses default if not provided)
        """
        self.config = config or Config()

    def extract_image_urls(self, html: str) -> List[Dict[str, Any]]:
        """
        Extract image URLs from HTML.

        Args:
            html: HTML content string

        Returns:
            List of dicts with url, width, height keys
        """
        images = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            for img in soup.find_all("img"):
                src = img.get("src")
                if src:
                    width = img.get("width")
                    height = img.get("height")

                    # Convert string dimensions to int if present
                    width = int(width) if width else None
                    height = int(height) if height else None

                    images.append(
                        {
                            "url": src,
                            "width": width,
                            "height": height,
                        }
                    )

            logger.info(f"Extracted {len(images)} images from HTML")
            return images

        except Exception as e:
            logger.error(f"Error extracting image URLs: {e}")
            return []

    def filter_tradingview_urls(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter for TradingView URLs.

        Args:
            images: List of image dicts

        Returns:
            Filtered list of TradingView images
        """
        tradingview_images = [img for img in images if "tradingview.com" in img["url"]]
        logger.info(f"Filtered {len(tradingview_images)} TradingView images")
        return tradingview_images

    async def download_images(
        self,
        image_urls: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Download images and encode to base64.

        Args:
            image_urls: List of image dicts with url, width, height

        Returns:
            List of image dicts with base64 data added
        """
        downloaded_images = []

        async with aiohttp.ClientSession() as session:
            for image_info in image_urls:
                try:
                    url = image_info["url"]
                    logger.info(f"Downloading image: {url}")

                    # Download image
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(self.config.image_download_timeout),
                    ) as resp:
                        if resp.status == 200:
                            image_bytes = await resp.read()

                            # Encode to base64
                            base64_data = base64.b64encode(image_bytes).decode("utf-8")

                            # Detect image format from Content-Type
                            content_type = resp.headers.get("content-type", "image/png")
                            image_format = self._extract_image_format(content_type)

                            # Create data URI
                            data_uri = f"data:{image_format};base64,{base64_data}"

                            downloaded_images.append(
                                {
                                    "url": url,
                                    "base64": data_uri,
                                    "width": image_info.get("width"),
                                    "height": image_info.get("height"),
                                }
                            )

                            logger.info(f"Successfully downloaded: {url}")
                        else:
                            logger.warning(f"Failed to download {url}: HTTP {resp.status}")

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout downloading image: {url}")
                except Exception as e:
                    logger.warning(f"Error downloading image {url}: {e}")

        return downloaded_images

    @staticmethod
    def _extract_image_format(content_type: str) -> str:
        """
        Extract image format from Content-Type header.

        Args:
            content_type: Content-Type header value

        Returns:
            Image format (e.g., "image/png")
        """
        # Extract just the image/* part
        match = re.search(r"image/[\w+]+", content_type)
        if match:
            return match.group(0)
        return "image/png"  # Default fallback
