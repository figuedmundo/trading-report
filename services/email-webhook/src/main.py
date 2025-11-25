"""
Email Webhook Service - Entry point for trading report automation pipeline.

Receives email payloads from external email service providers, validates signatures,
parses email content, detects trading reports, extracts URLs, and stores metadata
in PostgreSQL for downstream processing.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import logging
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from models import HealthResponse
from database import get_db_pool, init_connection_pool, close_connection_pool


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# FastAPI Application Setup
app = FastAPI(
    title="Email Webhook Service",
    version="0.1.0",
    description="Webhook endpoint for trading report notifications from email providers",
)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection pool on startup."""
    try:
        init_connection_pool()
        logger.info("Email Webhook Service started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection pool on shutdown."""
    try:
        close_connection_pool()
        logger.info("Email Webhook Service shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for service monitoring.

    Verifies the service is running and database is accessible.
    Returns 200 OK if healthy, 503 Service Unavailable if database unreachable.
    """
    try:
        # Try to get a connection to verify database connectivity
        pool = get_db_pool()
        if pool is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unavailable",
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "database": "disconnected",
                },
            )

        # Attempt to verify connection by querying the database
        try:
            conn = pool.getconn()
            try:
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT 1")
                    db_status = "connected"
                finally:
                    cursor.close()
            finally:
                pool.putconn(conn)
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            db_status = "disconnected"
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unavailable",
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "database": db_status,
                },
            )

        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "database": db_status,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "database": "disconnected",
            },
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
    )
