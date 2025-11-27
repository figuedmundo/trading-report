"""
FastAPI application entry point for notification service.

Sets up routes, middleware, startup/shutdown handlers, and lifespan management.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import Config, validate_config
from src.api.routes import router
from src.db.connection import init_db_pool, close_db_pool
from src.channels.factory import ChannelFactory
from src.templates.engine import TemplateEngine
from src.services.notification_service import NotificationService
from src.services.retry_scheduler import RetryScheduler
from src.utils.logger import get_logger
from src.utils.exceptions import ConfigurationError

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Unified Notification Service starting up")

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

    # Initialize channel factory
    try:
        channel_factory = ChannelFactory()
        await channel_factory.load_channels_from_config()
        app.state.channel_factory = channel_factory
        logger.info("Channel factory initialized")
    except Exception as e:
        logger.error(f"Failed to initialize channel factory: {str(e)}")
        raise

    # Initialize template engine
    try:
        template_engine = TemplateEngine()
        await template_engine.validate_templates_at_startup()
        logger.info("Template engine initialized and validated")
    except Exception as e:
        logger.error(f"Failed to initialize template engine: {str(e)}")
        raise

    # Initialize notification service
    try:
        notification_service = NotificationService(channel_factory, template_engine)
        app.state.notification_service = notification_service
        logger.info("Notification service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize notification service: {str(e)}")
        raise

    # Initialize retry scheduler
    try:
        retry_scheduler = RetryScheduler(notification_service)
        await retry_scheduler.start()
        app.state.retry_scheduler = retry_scheduler
        logger.info("Retry scheduler started")
    except Exception as e:
        logger.error(f"Failed to start retry scheduler: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Unified Notification Service shutting down")

    # Stop retry scheduler
    try:
        if hasattr(app.state, "retry_scheduler"):
            await app.state.retry_scheduler.stop()
            logger.info("Retry scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping retry scheduler: {str(e)}")

    # Close database pool
    await close_db_pool()
    logger.info("Database connection pool closed")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Unified Notification Service",
    version="0.1.0",
    description="Service for sending notifications via email, Telegram, and other channels",
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
