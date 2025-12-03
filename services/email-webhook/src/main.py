"""FastAPI application entry point for Email Webhook service.

Sets up routes, middleware stack, startup/shutdown handlers, and lifespan management.
Implements multi-layered security: IP ban → IP whitelist → Rate limit → Signature validation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from src.config import Config, get_config, validate_config
from src.api.routes import router
from src.db.connection import init_db_pool, close_db_pool
from src.utils.logger import get_logger
from src.utils.exceptions import SecurityError, IPBannedError, IPNotWhitelistedError, RateLimitExceededError, SignatureValidationError
from src.security.ban_manager import BanManager
from src.security.rate_limiter import RateLimiter
from src.security.rate_limit_storage import RateLimitStorage
from src.security.ip_allowlist_manager import IPAllowlistManager
from src.security.security_logger import SecurityLogger
from src.db.security_events_repository import SecurityEventsRepository
from src.security import signature_validator
from src.middleware.ip_ban_middleware import IPBanMiddleware
from src.middleware.ip_whitelist_middleware import IPWhitelistMiddleware
from src.middleware.rate_limit_middleware import RateLimitMiddleware
from src.middleware.signature_validation_middleware import SignatureValidationMiddleware
from fastapi.responses import JSONResponse

logger = get_logger(__name__)

# Global instances for middleware
ban_manager: BanManager = None
rate_limiter: RateLimiter = None
ip_allowlist_manager: IPAllowlistManager = None
security_logger: SecurityLogger = None
db_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    global ban_manager, rate_limiter, ip_allowlist_manager, security_logger, db_pool

    # Startup
    logger.info("Email Webhook Service starting up")

    # Load configuration
    config = get_config()
    if not validate_config():
        logger.warning("Configuration validation incomplete - some values may be missing")

    # Initialize database connection pool
    try:
        db_pool = await init_db_pool()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {str(e)}")
        raise

    # Initialize IP ban manager and load persisted bans
    try:
        ban_manager = BanManager(config=config, db_pool=db_pool)
        await ban_manager.load_from_database()
        logger.info("IP ban manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize ban manager: {str(e)}")
        raise

    # Initialize IP allowlist manager
    try:
        ip_allowlist_manager = IPAllowlistManager()
        await ip_allowlist_manager.initialize()
        logger.info("IP allowlist manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize IP allowlist manager: {str(e)}")
        raise

    # Initialize rate limiter
    try:
        rate_limit_storage = RateLimitStorage()
        rate_limiter = RateLimiter(config=config, storage=rate_limit_storage)
        logger.info("Rate limiter initialized")
    except Exception as e:
        logger.error(f"Failed to initialize rate limiter: {str(e)}")
        raise

    # Initialize security logger
    try:
        security_events_repo = SecurityEventsRepository()
        security_logger = SecurityLogger(security_events_repo)
        logger.info("Security logger initialized")
    except Exception as e:
        logger.error(f"Failed to initialize security logger: {str(e)}")
        raise

    # Start background cleanup task
    cleanup_task = asyncio.create_task(_cleanup_task())
    logger.info("Background cleanup task started")

    yield

    # Shutdown
    logger.info("Email Webhook Service shutting down")

    # Cancel cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # Sync bans to database
    try:
        if ban_manager:
            await ban_manager.sync_to_database()
        logger.info("IP bans synced to database")
    except Exception as e:
        logger.error(f"Failed to sync bans to database: {str(e)}")

    # Close database pool
    try:
        await close_db_pool()
        logger.info("Database connection pool closed")
    except Exception as e:
        logger.error(f"Failed to close database pool: {str(e)}")


async def _cleanup_task():
    """Background task to cleanup expired rate limits and bans every 60 seconds."""
    global ban_manager, rate_limiter

    while True:
        try:
            await asyncio.sleep(60)

            # Cleanup expired bans
            if ban_manager:
                removed_count = ban_manager.cleanup_expired_bans()
                if removed_count > 0:
                    logger.debug(f"Cleaned up {removed_count} expired bans")

            # Cleanup expired rate limits
            if rate_limiter:
                removed_count = rate_limiter.storage.cleanup_expired()
                if removed_count > 0:
                    logger.debug(f"Cleaned up {removed_count} expired rate limit entries")

            # Sync bans to database (every 5 minutes internally)
            if ban_manager:
                await ban_manager.sync_to_database()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Email Webhook Service",
    version="0.1.0",
    description="Secure webhook endpoint for email notifications with multi-layered security",
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


# Add security middleware stack in correct order
# Important: Add in reverse order because they wrap each other
def add_security_middleware():
    """Add security middleware stack after initialization."""
    global ban_manager, rate_limiter, ip_allowlist_manager, security_logger

    # Layer 4: Signature validation (final layer, applies to /webhook/*)
    if signature_validator:
        app.add_middleware(
            SignatureValidationMiddleware,
            signature_validator=signature_validator,
            ban_manager=ban_manager,
            security_logger=security_logger,
        )

    # Layer 3: Rate limiting
    if rate_limiter:
        app.add_middleware(
            RateLimitMiddleware,
            rate_limiter=rate_limiter,
            ban_manager=ban_manager,
            security_logger=security_logger,
        )

    # Layer 2: IP whitelist
    if ip_allowlist_manager:
        app.add_middleware(
            IPWhitelistMiddleware,
            ip_allowlist_manager=ip_allowlist_manager,
            ban_manager=ban_manager,
            security_logger=security_logger,
        )

    # Layer 1: IP ban (first layer, checks immediately)
    if ban_manager:
        app.add_middleware(
            IPBanMiddleware,
            ban_manager=ban_manager,
        )


# Exception handlers for security errors
@app.exception_handler(IPBannedError)
async def ip_banned_exception_handler(request, exc):
    """Handle IP banned exceptions."""
    return JSONResponse(
        status_code=403,
        content={"error": "Access denied", "code": "IP_BANNED"},
    )


@app.exception_handler(IPNotWhitelistedError)
async def ip_not_whitelisted_exception_handler(request, exc):
    """Handle IP not whitelisted exceptions."""
    return JSONResponse(
        status_code=403,
        content={"error": "Access denied", "code": "IP_NOT_WHITELISTED"},
    )


@app.exception_handler(RateLimitExceededError)
async def rate_limit_exceeded_exception_handler(request, exc):
    """Handle rate limit exceeded exceptions."""
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded", "code": "RATE_LIMIT_EXCEEDED"},
    )


@app.exception_handler(SignatureValidationError)
async def signature_validation_exception_handler(request, exc):
    """Handle signature validation exceptions."""
    return JSONResponse(
        status_code=401,
        content={"error": "Unauthorized", "code": "INVALID_SIGNATURE"},
    )


@app.exception_handler(SecurityError)
async def security_error_exception_handler(request, exc):
    """Handle generic security errors."""
    return JSONResponse(
        status_code=400,
        content={"error": "Security error", "code": "SECURITY_ERROR"},
    )


# Health check endpoint (no security middleware)
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint.

    Returns service status. Bypassed by all security middleware
    to prevent monitoring lockout.
    """
    return {"status": "ok", "service": "email-webhook"}


# Include API routes
app.include_router(router)


# Add security middleware after app creation (after lifespan)
# This is a bit of a hack but necessary because middleware needs access to
# globals that are initialized in the lifespan startup
startup_done = False


@app.on_event("startup")
async def startup_event():
    """Called after lifespan startup, add middleware here."""
    global startup_done
    if not startup_done:
        add_security_middleware()
        startup_done = True
        logger.info("Security middleware stack initialized")
