"""
FastAPI application entry point for Health Monitoring service.

Sets up routes, middleware, startup/shutdown handlers, and background tasks
for health checks, alert generation, and data cleanup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timezone, timedelta

from src.config import Config, validate_config
from src.api.routes import router, set_health_check_service
from src.services.health_check_service import HealthCheckService
from src.services.alert_service import AlertService
from src.services.cleanup_service import CleanupService
from src.db.connection import init_db_pool, close_db_pool
from src.utils.logger import get_logger
from src.utils.exceptions import ConfigurationError

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Health Monitoring Service starting up")

    config = Config()
    if not validate_config():
        logger.warning("Configuration validation incomplete - some values may be missing")

    # Initialize database connection pool
    try:
        await init_db_pool()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {str(e)}")
        raise

    # Initialize services
    try:
        health_check_service = HealthCheckService()
        set_health_check_service(health_check_service)
        logger.info("Health check service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize health check service: {str(e)}")
        raise

    alert_service = AlertService()
    cleanup_service = CleanupService()

    # Start background tasks
    health_check_task = asyncio.create_task(_health_check_loop(health_check_service))
    logger.info("Health check scheduler started")

    alert_generation_task = asyncio.create_task(_alert_generation_loop(alert_service))
    logger.info("Alert generation scheduler started")

    cleanup_task = asyncio.create_task(_cleanup_loop(cleanup_service))
    logger.info("Data cleanup scheduler started")

    yield

    # Shutdown
    logger.info("Health Monitoring Service shutting down")

    # Cancel background tasks
    health_check_task.cancel()
    alert_generation_task.cancel()
    cleanup_task.cancel()

    try:
        await health_check_task
    except asyncio.CancelledError:
        logger.info("Health check loop cancelled")
        pass

    try:
        await alert_generation_task
    except asyncio.CancelledError:
        logger.info("Alert generation loop cancelled")
        pass

    try:
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("Cleanup loop cancelled")
        pass

    await close_db_pool()
    logger.info("Database connection pool closed")


async def _health_check_loop(health_check_service: HealthCheckService) -> None:
    """
    Background task for periodic health checks.

    Runs health checks every HEALTH_CHECK_INTERVAL seconds and stores results.
    """
    from src.db.health_repository import HealthRepository

    config = Config()

    while True:
        try:
            logger.debug("Running health checks...")
            results = await health_check_service.run_all_checks()

            for result in results:
                try:
                    await HealthRepository.store_health_check(
                        service_name=result["service_name"],
                        status=result["status"],
                        check_duration_ms=result["check_duration_ms"],
                        details=result.get("details"),
                    )
                except Exception as e:
                    logger.error(f"Failed to store health check: {str(e)}")

            logger.debug("Health checks completed")
            await asyncio.sleep(config.health_check_interval)

        except asyncio.CancelledError:
            logger.info("Health check loop cancelled")
            break
        except Exception as e:
            logger.error(f"Health check loop error: {str(e)}")
            await asyncio.sleep(config.health_check_interval)


async def _alert_generation_loop(alert_service: AlertService) -> None:
    """
    Background task for periodic alert generation and delivery.

    Runs every 60 seconds to check for critical errors and generate alerts.
    """
    while True:
        try:
            logger.debug("Checking for critical errors...")
            alerts = await alert_service.check_and_generate_alerts()

            if alerts:
                logger.info(f"Generating {len(alerts)} alerts")
                await alert_service.send_alerts(alerts)

            await asyncio.sleep(60)

        except asyncio.CancelledError:
            logger.info("Alert generation loop cancelled")
            break
        except Exception as e:
            logger.error(f"Alert generation loop error: {str(e)}")
            await asyncio.sleep(60)


async def _cleanup_loop(cleanup_service: CleanupService) -> None:
    """
    Background task for daily data cleanup.

    Runs daily at midnight UTC to clean up old error logs and health checks.
    """
    while True:
        try:
            # Calculate time until next midnight
            now = datetime.now(timezone.utc)
            midnight_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # If we're past midnight, schedule for tomorrow
            if now > midnight_today:
                next_midnight = midnight_today + timedelta(days=1)
            else:
                next_midnight = midnight_today

            seconds_until_midnight = (next_midnight - now).total_seconds()
            logger.debug(
                f"Cleanup scheduled for {next_midnight.isoformat()} "
                f"({seconds_until_midnight} seconds from now)"
            )

            # Sleep until midnight
            await asyncio.sleep(seconds_until_midnight)

            logger.info("Running data cleanup...")
            result = await cleanup_service.cleanup_all()
            logger.info(f"Cleanup completed: {result}")

        except asyncio.CancelledError:
            logger.info("Cleanup loop cancelled")
            break
        except Exception as e:
            logger.error(f"Cleanup loop error: {str(e)}")
            # Sleep and retry in 1 hour
            await asyncio.sleep(3600)


# Create FastAPI app with lifespan
app = FastAPI(
    title="Health Monitoring Service",
    version="0.1.0",
    description="System-wide health monitoring, error logging, and alert generation",
    lifespan=lifespan,
)

# Add CORS middleware for service-to-service communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)
