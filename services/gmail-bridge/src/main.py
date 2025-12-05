"""Gmail Bridge Service - FastAPI Application."""

import asyncio
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .config import Config
from .models import HealthStatus, ServiceInfo
from .gmail_poller import GmailPoller

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "gmail-bridge", "message": "%(message)s"}',
)
logger = logging.getLogger(__name__)

# Global poller instance
poller: GmailPoller = None
start_time: datetime = None


# Initialize FastAPI app
app = FastAPI(
    title="Gmail Bridge Service",
    description="Polls Gmail inbox and forwards trading reports to webhook",
    version="0.1.0",
)


@app.on_event("startup")
async def startup_event():
    """FastAPI startup event handler."""
    global poller, start_time

    logger.info("Starting Gmail Bridge service")
    start_time = datetime.utcnow()

    Config.validate()

    # Initialize and start poller
    poller = GmailPoller()
    poller.poll_task = asyncio.create_task(poller.run())
    logger.info("Polling task started in background")


@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI shutdown event handler."""
    logger.info("Shutting down Gmail Bridge service")
    if poller:
        poller.stop()
        if poller.poll_task:
            try:
                await asyncio.wait_for(poller.poll_task, timeout=5)
            except asyncio.TimeoutError:
                logger.warning("Polling task did not complete within 5 seconds")
                poller.poll_task.cancel()
                try:
                    await poller.poll_task
                except asyncio.CancelledError:
                    pass
    logger.info("Gmail Bridge service stopped")


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    if not poller:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "service": "gmail-bridge",
                "version": "0.1.0",
                "imap_connected": False,
                "message": "Service not initialized",
            },
        )

    return {
        "status": "ok" if poller.is_running else "error",
        "service": "gmail-bridge",
        "version": "0.1.0",
        "imap_connected": poller.imap_client is not None,
        "last_poll": poller.last_poll_time,
        "emails_processed": poller.total_emails_processed,
        "next_poll": poller.next_poll_time,
    }


@app.get("/api/v1/status")
async def get_status() -> ServiceInfo:
    """Get detailed service status and statistics."""
    if not poller:
        raise HTTPException(status_code=503, detail="Service not initialized")

    uptime_seconds = int(
        (datetime.utcnow() - start_time).total_seconds() if start_time else 0
    )

    return ServiceInfo(
        status="running" if poller.is_running else "stopped",
        uptime_seconds=uptime_seconds,
        total_emails_processed=poller.total_emails_processed,
        total_errors=poller.total_errors,
        poll_interval_seconds=Config.POLL_INTERVAL,
        imap_host=Config.IMAP_HOST,
        webhook_configured=bool(Config.WEBHOOK_URL),
        last_poll_timestamp=poller.last_poll_time,
        next_poll_timestamp=poller.next_poll_time,
    )


@app.post("/api/v1/poll")
async def trigger_manual_poll() -> dict:
    """Manually trigger a polling cycle (for testing/debugging)."""
    if not poller:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if not poller.imap_client:
        raise HTTPException(status_code=503, detail="IMAP client not connected")

    try:
        stats = await poller.poll_once()
        return {
            "success": True,
            "timestamp": stats.timestamp.isoformat(),
            "messages_found": stats.messages_found,
            "new_messages": stats.new_messages,
            "successfully_processed": stats.successfully_processed,
            "failed_count": stats.failed_count,
            "errors": stats.errors,
        }
    except Exception as e:
        logger.error(f"Manual poll failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/config")
async def get_config() -> dict:
    """Get current service configuration (for debugging)."""
    return {
        "service": "gmail-bridge",
        "imap_host": Config.IMAP_HOST,
        "imap_port": Config.IMAP_PORT,
        "poll_interval": Config.POLL_INTERVAL,
        "search_criteria": Config.EMAIL_SEARCH_CRITERIA,
        "sender_filter": "***" if Config.EMAIL_SENDER_FILTER else None,
        "webhook_configured": bool(Config.WEBHOOK_URL),
        "mark_as_read": Config.MARK_AS_READ,
    }


@app.get("/")
async def root() -> dict:
    """Root endpoint with service information."""
    return {
        "service": "gmail-bridge",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "status": "/api/v1/status",
            "poll": "/api/v1/poll (POST)",
            "config": "/api/v1/config",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.SERVICE_PORT,
        log_level=Config.LOG_LEVEL.lower(),
    )
