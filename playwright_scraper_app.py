"""
Trading Report Playwright Scraper Service
FastAPI service for automated browser-based report scraping
"""

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from config import settings
from models.request import ScrapeRequest
from models.response import ScrapeResponse, HealthResponse
from scraper.browser import BrowserManager
from scraper.report_extractor import ReportExtractor
from utils.logger import setup_logging

# Setup structured logging
setup_logging()
logger = structlog.get_logger()

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key for authentication."""
    if api_key != settings.API_KEY:
        logger.warning("invalid_api_key_attempt", provided_key=api_key[:8] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return api_key


# Browser manager instance
browser_manager: BrowserManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global browser_manager
    
    logger.info("starting_playwright_scraper_service", version="1.0.0")
    
    # Initialize browser manager
    browser_manager = BrowserManager(
        headless=settings.BROWSER_HEADLESS,
        timeout=settings.SCRAPE_TIMEOUT,
    )
    await browser_manager.initialize()
    
    logger.info("playwright_scraper_service_started")
    
    yield
    
    # Cleanup
    logger.info("shutting_down_playwright_scraper_service")
    if browser_manager:
        await browser_manager.close()
    logger.info("playwright_scraper_service_stopped")


# Initialize FastAPI app
app = FastAPI(
    title="Trading Report Scraper",
    description="Automated browser-based scraping service for trading reports",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="playwright-scraper",
        version="1.0.0",
    )


@app.post("/api/v1/scrape", response_model=ScrapeResponse, tags=["Scraping"])
async def scrape_report(
    request: ScrapeRequest,
    api_key: str = Security(verify_api_key),
) -> ScrapeResponse:
    """
    Scrape a trading report from the provided URL.
    
    This endpoint:
    1. Launches a browser
    2. Logs into the trading portal
    3. Navigates to the report URL
    4. Extracts text content and images
    5. Returns structured data
    """
    logger.info(
        "scrape_request_received",
        url=request.url,
        extract_images=request.options.extract_images,
    )
    
    if not browser_manager:
        logger.error("browser_manager_not_initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Browser manager not initialized",
        )
    
    try:
        # Create report extractor
        extractor = ReportExtractor(
            browser_manager=browser_manager,
            credentials=request.credentials,
            options=request.options,
        )
        
        # Extract report data
        result = await extractor.extract_report(request.url)
        
        logger.info(
            "scrape_completed_successfully",
            url=request.url,
            text_length=len(result["text_content"]),
            image_count=len(result["images"]),
            duration_ms=result["metadata"]["duration_ms"],
        )
        
        return ScrapeResponse(
            success=True,
            data=result,
        )
        
    except Exception as e:
        logger.error(
            "scrape_failed",
            url=request.url,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scraping failed: {str(e)}",
        )


@app.get("/api/v1/metrics", tags=["Monitoring"])
async def get_metrics(api_key: str = Security(verify_api_key)) -> dict[str, Any]:
    """Get service metrics."""
    if not browser_manager:
        return {"error": "Browser manager not initialized"}
    
    return {
        "active_contexts": browser_manager.active_contexts,
        "total_scrapes": browser_manager.total_scrapes,
        "failed_scrapes": browser_manager.failed_scrapes,
        "uptime_seconds": browser_manager.uptime_seconds,
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
