"""
FastAPI application entry point for Playwright scraper service.

Sets up routes, middleware, and startup/shutdown handlers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.config import Config, validate_config
from src.api.routes import router
from src.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Playwright scraper service starting up")
    config = Config()
    if not validate_config():
        logger.warning("Configuration validation incomplete - some values may be missing")

    yield

    # Shutdown
    logger.info("Playwright scraper service shutting down")


# Create FastAPI app with lifespan
app = FastAPI(
    title="playwright-scraper",
    version="0.1.0",
    description="Browser automation service for trading portal scraping",
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
