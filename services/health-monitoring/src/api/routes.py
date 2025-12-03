"""
API routes for health monitoring and error logging endpoints.

Provides REST API for operators to query health status, errors, and trigger manual checks.
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional, List
import json

from src.models import (
    HealthCheckResponse,
    AggregateHealthResponse,
    ErrorLogListResponse,
    ErrorLogEntry,
    ErrorResponse,
)
from src.services.health_check_service import HealthCheckService
from src.db.health_repository import HealthRepository
from src.db.error_repository import ErrorRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Global service instance
health_check_service: Optional[HealthCheckService] = None


def set_health_check_service(service: HealthCheckService) -> None:
    """Set the health check service instance for routes to use."""
    global health_check_service
    health_check_service = service


@router.get("/health")
async def get_health() -> dict:
    """
    Get health status of this service.

    Minimal response for Docker healthcheck. Returns quickly.

    Returns:
        Health status response
    """
    return {
        "status": "ok",
        "service": "health-monitoring",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/v1/health/status")
async def get_aggregate_health() -> AggregateHealthResponse:
    """
    Get aggregate health status of all services.

    Queries latest health check for each service and calculates overall status.
    Overall status: "healthy" (all up), "degraded" (some up), "unhealthy" (all down).

    Returns:
        Aggregate health status with all services
    """
    try:
        latest_checks = await HealthRepository.get_latest_health_checks()

        if not latest_checks:
            raise HTTPException(
                status_code=500,
                detail="No health checks available",
            )

        # Calculate overall status
        statuses = [check["status"] for check in latest_checks]
        up_count = sum(1 for s in statuses if s == "up")
        total_count = len(statuses)

        if up_count == total_count:
            overall_status = "healthy"
        elif up_count == 0:
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        # Convert to response models
        services = [
            HealthCheckResponse(
                service_name=check["service_name"],
                status=check["status"],
                check_timestamp=check["check_timestamp"],
                check_duration_ms=check["check_duration_ms"],
                details=json.loads(check.get("details")) if isinstance(check.get("details"), str) else check.get("details"),
            )
            for check in latest_checks
        ]

        response = AggregateHealthResponse(
            timestamp=datetime.now(timezone.utc),
            overall_status=overall_status,
            services=services,
        )

        # Return appropriate status code
        status_code = 200 if overall_status == "healthy" else 503
        # Note: FastAPI doesn't let us set response code directly here,
        # so we return 200 for all. Caller should check overall_status.
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get aggregate health: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve health status",
        )


@router.get("/api/v1/health/errors")
async def get_errors(
    severity: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    hours: int = Query(24),
    limit: int = Query(10),
) -> ErrorLogListResponse:
    """
    Get error logs filtered by severity, service, and time window.

    Query Parameters:
        - severity: Filter by severity (CRITICAL, ERROR, WARNING)
        - service: Filter by service name
        - hours: Number of hours to look back (default: 24)
        - limit: Maximum number of records to return (default: 10)

    Returns:
        List of error log entries
    """
    try:
        # Validate parameters
        if severity and severity not in ["CRITICAL", "ERROR", "WARNING"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid severity. Must be CRITICAL, ERROR, or WARNING.",
            )

        if hours < 1 or hours > 365:
            raise HTTPException(
                status_code=400,
                detail="Hours must be between 1 and 365.",
            )

        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 1000.",
            )

        # Retrieve errors
        errors = await ErrorRepository.get_recent_errors(
            severity=severity,
            service=service,
            hours=hours,
            limit=limit,
        )

        # Convert to response models
        error_entries = [
            ErrorLogEntry(
                id=error["id"],
                error_timestamp=error["error_timestamp"],
                service_name=error["service_name"],
                error_type=error["error_type"],
                severity=error["severity"],
                message=error["message"],
                context_json=error["context_json"],
                source_report_id=error["source_report_id"],
                stack_trace=error["stack_trace"],
                correlation_id=error["correlation_id"],
                created_at=error["created_at"],
            )
            for error in errors
        ]

        return ErrorLogListResponse(
            timestamp=datetime.now(timezone.utc),
            count=len(error_entries),
            errors=error_entries,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve errors: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve errors",
        )


@router.post("/api/v1/health/check/{service_name}")
async def trigger_health_check(service_name: str) -> HealthCheckResponse:
    """
    Manually trigger a health check for a specific service.

    Path Parameters:
        - service_name: One of (email-webhook, playwright-scraper, ai-analyzer,
                       notification-service, n8n)

    Returns:
        Health check result for the service
    """
    try:
        if not health_check_service:
            raise HTTPException(
                status_code=500,
                detail="Health check service not initialized",
            )

        # Map service name to check function
        check_methods = {
            "email-webhook": health_check_service.check_email_webhook,
            "playwright-scraper": health_check_service.check_playwright_scraper,
            "ai-analyzer": health_check_service.check_ai_analyzer,
            "notification-service": health_check_service.check_notification_service,
            "n8n": health_check_service.check_n8n,
        }

        if service_name not in check_methods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid service name. Must be one of: {list(check_methods.keys())}",
            )

        # Run the check
        result = await check_methods[service_name]()

        # Store result to database
        await HealthRepository.store_health_check(
            service_name=result["service_name"],
            status=result["status"],
            check_duration_ms=result["check_duration_ms"],
            details=result.get("details"),
        )

        # Return response
        return HealthCheckResponse(
            service_name=result["service_name"],
            status=result["status"],
            check_timestamp=result["check_timestamp"],
            check_duration_ms=result["check_duration_ms"],
            details=result.get("details"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger health check: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to trigger health check",
        )
