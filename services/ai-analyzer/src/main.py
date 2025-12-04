"""
FastAPI application entry point for AI analysis service.

Sets up routes, middleware, startup/shutdown handlers, and lifespan management.
Validates configuration and initializes all services on startup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import Config, validate_config
from src.api.routes import router, set_analysis_service
from src.services.analysis_service import AnalysisService
from src.db.connection import init_db_pool, close_db_pool
from src.utils.logger import get_logger
from src.utils.exceptions import ConfigurationError

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("AI Analysis Engine service starting up")

    config = Config()

    # Validate configuration - fail fast if required vars missing
    if not validate_config():
        error_msg = "Configuration validation failed - check environment variables"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)

    # Log configuration details
    logger.info(
        "Configuration loaded successfully",
        extra={
            "llm_model": config.llm_model,
            "thinking_budget_tokens": config.thinking_budget_tokens,
            "service_port": config.service_port,
            "analysis_timeout": config.analysis_timeout,
        }
    )

    # Initialize database connection pool
    try:
        await init_db_pool()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {str(e)}")
        raise

    # Initialize analysis service (this will trigger provider detection)
    try:
        analysis_service = AnalysisService()
        set_analysis_service(analysis_service)
        logger.info("Analysis service initialized successfully")
    except ConfigurationError as e:
        logger.error(f"Configuration error during service initialization: {e.message}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize analysis service: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("AI Analysis Engine service shutting down")
    await close_db_pool()
    logger.info("Database connection pool closed")


# Create FastAPI app with lifespan
app = FastAPI(
    title="AI Analysis Engine",
    version="0.1.0",
    description="Service for analyzing trading reports and extracting signals using LLM with extended thinking support",
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
