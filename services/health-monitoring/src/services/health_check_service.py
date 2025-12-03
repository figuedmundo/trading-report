"""
Health check service for monitoring all microservices.

Performs periodic health checks on all services and stores results.
"""

import aiohttp
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional
import time

from src.config import get_config
from src.utils.logger import get_logger
from src.utils.exceptions import HealthCheckError

logger = get_logger(__name__)


class HealthCheckService:
    """Service for checking health of all microservices."""

    def __init__(self):
        """Initialize health check service."""
        self.config = get_config()

    async def check_email_webhook(self) -> Dict:
        """
        Check health of email-webhook service.

        Returns:
            Health check result dictionary
        """
        return await self._check_service(
            "email-webhook",
            f"{self.config.email_webhook_url}/health",
        )

    async def check_playwright_scraper(self) -> Dict:
        """
        Check health of playwright-scraper service.

        Returns:
            Health check result dictionary
        """
        return await self._check_service(
            "playwright-scraper",
            f"{self.config.playwright_scraper_url}/health",
        )

    async def check_ai_analyzer(self) -> Dict:
        """
        Check health of ai-analyzer service.

        Returns:
            Health check result dictionary
        """
        return await self._check_service(
            "ai-analyzer",
            f"{self.config.ai_analyzer_url}/health",
        )

    async def check_notification_service(self) -> Dict:
        """
        Check health of notification-service.

        Returns:
            Health check result dictionary
        """
        return await self._check_service(
            "notification-service",
            f"{self.config.notification_service_health_url}/health",
        )

    async def check_n8n(self) -> Dict:
        """
        Check health of N8N service.

        Returns:
            Health check result dictionary
        """
        return await self._check_service(
            "n8n",
            f"{self.config.n8n_url}/",
        )

    async def _check_service(
        self,
        service_name: str,
        health_url: str,
    ) -> Dict:
        """
        Check health of a service via HTTP.

        Args:
            service_name: Name of the service
            health_url: URL of the health endpoint

        Returns:
            Health check result with status, duration_ms, and details
        """
        start_time = time.time()
        status = "down"
        duration_ms = 0
        details = {}

        try:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        health_url,
                        timeout=aiohttp.ClientTimeout(
                            total=self.config.health_check_timeout
                        ),
                    ) as response:
                        duration_ms = int((time.time() - start_time) * 1000)

                        if response.status == 200:
                            status = "up"
                            try:
                                details = await response.json()
                            except Exception:
                                details = {"response": "ok"}
                        else:
                            status = "degraded"
                            details = {"http_status": response.status}

                except asyncio.TimeoutError:
                    duration_ms = int((time.time() - start_time) * 1000)
                    status = "down"
                    details = {"error": "timeout"}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            status = "down"
            details = {"error": str(e)}
            logger.warning(
                f"Health check failed for {service_name}: {str(e)}"
            )

        logger.info(
            f"Health check result: service={service_name}, status={status}, "
            f"duration_ms={duration_ms}"
        )

        return {
            "service_name": service_name,
            "status": status,
            "check_timestamp": datetime.now(timezone.utc),
            "check_duration_ms": duration_ms,
            "details": details,
        }

    async def run_all_checks(self) -> List[Dict]:
        """
        Run health checks for all services.

        Returns:
            List of health check results
        """
        checks = [
            self.check_email_webhook(),
            self.check_playwright_scraper(),
            self.check_ai_analyzer(),
            self.check_notification_service(),
            self.check_n8n(),
        ]

        results = await asyncio.gather(*checks, return_exceptions=False)
        return [r for r in results if isinstance(r, dict)]
