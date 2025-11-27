"""
Credential Service - Secure credential management with encrypted storage.

REST API service for managing trading portal credentials with encryption,
audit logging, and per-report credential override support.
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import logging
import sys
import os
import uuid
from typing import Optional

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from schemas import (
    CredentialRequest,
    CredentialResponse,
    CredentialListResponse,
    ErrorResponse,
    HealthResponse,
)
from database import (
    get_db_pool,
    init_connection_pool,
    close_connection_pool,
    create_credential,
    get_credential_by_domain,
    get_credential_by_id,
    update_credential,
    delete_credential,
    list_all_credentials,
)
from config import get_config
from logging_utils import sanitize_log_message
import psycopg2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# FastAPI Application Setup
app = FastAPI(
    title='Credential Service',
    version='0.1.0',
    description='Secure credential management API with encryption and audit logging',
)


@app.on_event('startup')
async def startup_event():
    """Initialize database connection pool on startup."""
    try:
        init_connection_pool()
        logger.info('Credential Service started successfully')
    except Exception as e:
        logger.error(f'Failed to initialize connection pool: {e}')
        raise


@app.on_event('shutdown')
async def shutdown_event():
    """Close database connection pool on shutdown."""
    try:
        close_connection_pool()
        logger.info('Credential Service shut down successfully')
    except Exception as e:
        logger.error(f'Error during shutdown: {e}')


def _generate_correlation_id() -> str:
    """Generate or retrieve correlation ID."""
    return str(uuid.uuid4())


def _get_current_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


@app.get('/health', response_model=HealthResponse)
async def health_check(request: Request):
    """
    Health check endpoint for service monitoring.

    Verifies the service is running and database is accessible.
    Returns 200 OK if healthy, 503 Service Unavailable if database unreachable.
    """
    correlation_id = _generate_correlation_id()

    try:
        # Try to get a connection to verify database connectivity
        pool = get_db_pool()
        if pool is None:
            logger.warning('Database pool is None')
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    'status': 'unavailable',
                    'database_connected': False,
                    'timestamp': _get_current_timestamp().isoformat(),
                    'correlation_id': correlation_id,
                },
            )

        # Attempt to verify connection by querying the database
        try:
            conn = pool.getconn()
            try:
                cursor = conn.cursor()
                try:
                    cursor.execute('SELECT 1')
                    db_status = True
                finally:
                    cursor.close()
            finally:
                pool.putconn(conn)
        except Exception as e:
            logger.warning(f'Database health check failed: {e}')
            db_status = False
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    'status': 'unavailable',
                    'database_connected': db_status,
                    'timestamp': _get_current_timestamp().isoformat(),
                    'correlation_id': correlation_id,
                },
            )

        return {
            'status': 'ok',
            'database_connected': db_status,
            'timestamp': _get_current_timestamp(),
            'correlation_id': correlation_id,
        }
    except Exception as e:
        logger.error(f'Health check failed: {e}')
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                'status': 'unavailable',
                'database_connected': False,
                'timestamp': _get_current_timestamp().isoformat(),
                'correlation_id': correlation_id,
            },
        )


@app.post('/api/v1/credentials', response_model=CredentialResponse, status_code=201)
async def create_credential_endpoint(request: CredentialRequest):
    """
    Create a new credential with encrypted password.

    Request body:
        - domain: Portal domain (must be unique)
        - username: Portal username
        - password: Portal password (will be encrypted)
        - metadata: Optional portal-specific metadata

    Returns:
        - 201 Created: Credential created successfully
        - 409 Conflict: Credential already exists for domain
        - 500 Internal Server Error: Encryption or database error
    """
    correlation_id = _generate_correlation_id()

    try:
        # Create credential
        result = create_credential(
            domain=request.domain,
            username=request.username,
            password=request.password,
            metadata=request.metadata,
        )

        logger.info(f'Credential created for domain {request.domain}, correlation_id={correlation_id}')

        return CredentialResponse(
            **result,
            correlation_id=correlation_id,
        )

    except psycopg2.IntegrityError as e:
        logger.warning(f'Duplicate credential domain {request.domain}, correlation_id={correlation_id}')
        raise HTTPException(
            status_code=409,
            detail=f'Credential already exists for domain {request.domain}',
        )
    except Exception as e:
        logger.error(f'Failed to create credential: {e}, correlation_id={correlation_id}')
        raise HTTPException(
            status_code=500,
            detail='Failed to create credential',
        )


@app.get('/api/v1/credentials', response_model=CredentialListResponse)
async def list_credentials_endpoint():
    """
    List all credentials (without passwords for security).

    Returns:
        - 200 OK: List of credentials
        - 500 Internal Server Error: Database error
    """
    correlation_id = _generate_correlation_id()

    try:
        credentials = list_all_credentials()
        logger.debug(f'Listed {len(credentials)} credentials, correlation_id={correlation_id}')

        return CredentialListResponse(
            credentials=[
                CredentialResponse(
                    **cred,
                    correlation_id=correlation_id,
                )
                for cred in credentials
            ],
            total=len(credentials),
            correlation_id=correlation_id,
        )

    except Exception as e:
        logger.error(f'Failed to list credentials: {e}, correlation_id={correlation_id}')
        raise HTTPException(
            status_code=500,
            detail='Failed to list credentials',
        )


@app.get('/api/v1/credentials/domain/{domain}', response_model=CredentialResponse)
async def get_credential_by_domain_endpoint(domain: str):
    """
    Retrieve active credential by domain with decrypted password.

    Path parameter:
        - domain: Portal domain to look up

    Returns:
        - 200 OK: Credential found and decrypted
        - 404 Not Found: No active credential for domain
        - 500 Internal Server Error: Decryption failure
    """
    correlation_id = _generate_correlation_id()

    try:
        credential = get_credential_by_domain(domain)

        if not credential:
            logger.warning(f'Credential not found for domain {domain}, correlation_id={correlation_id}')
            raise HTTPException(
                status_code=404,
                detail=f'No active credential found for domain {domain}',
            )

        logger.debug(f'Retrieved credential for domain {domain}, correlation_id={correlation_id}')

        return CredentialResponse(
            **credential,
            correlation_id=correlation_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to retrieve credential for domain {domain}: {e}, correlation_id={correlation_id}')
        raise HTTPException(
            status_code=500,
            detail=f'Failed to decrypt credentials for domain {domain}',
        )


@app.get('/api/v1/credentials/{credential_id}', response_model=CredentialResponse)
async def get_credential_by_id_endpoint(credential_id: str):
    """
    Retrieve credential by ID with decrypted password.

    Path parameter:
        - credential_id: UUID of credential

    Returns:
        - 200 OK: Credential found and decrypted
        - 404 Not Found: Credential not found
        - 500 Internal Server Error: Decryption failure
    """
    correlation_id = _generate_correlation_id()

    try:
        credential = get_credential_by_id(credential_id)

        if not credential:
            logger.warning(f'Credential not found: {credential_id}, correlation_id={correlation_id}')
            raise HTTPException(
                status_code=404,
                detail=f'Credential not found: {credential_id}',
            )

        logger.debug(f'Retrieved credential {credential_id}, correlation_id={correlation_id}')

        return CredentialResponse(
            **credential,
            correlation_id=correlation_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to retrieve credential {credential_id}: {e}, correlation_id={correlation_id}')
        raise HTTPException(
            status_code=500,
            detail='Failed to decrypt credentials',
        )


@app.put('/api/v1/credentials/{credential_id}', response_model=CredentialResponse)
async def update_credential_endpoint(credential_id: str, request: CredentialRequest):
    """
    Update credential with new encrypted password.

    Path parameter:
        - credential_id: UUID of credential to update

    Request body:
        - domain: Portal domain (ignored, uses existing)
        - username: New username
        - password: New password (will be encrypted)
        - metadata: Optional new metadata

    Returns:
        - 200 OK: Credential updated successfully
        - 404 Not Found: Credential not found
        - 500 Internal Server Error: Update failed
    """
    correlation_id = _generate_correlation_id()

    try:
        # Check if credential exists
        existing = get_credential_by_id(credential_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f'Credential not found: {credential_id}',
            )

        # Update credential
        result = update_credential(
            credential_id=credential_id,
            username=request.username,
            password=request.password,
            metadata=request.metadata,
        )

        logger.info(f'Credential updated: {credential_id}, correlation_id={correlation_id}')

        return CredentialResponse(
            **result,
            correlation_id=correlation_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to update credential {credential_id}: {e}, correlation_id={correlation_id}')
        raise HTTPException(
            status_code=500,
            detail='Failed to update credential',
        )


@app.delete('/api/v1/credentials/{credential_id}', status_code=204)
async def delete_credential_endpoint(credential_id: str):
    """
    Delete (deactivate) credential.

    This is a logical delete to preserve audit trail.

    Path parameter:
        - credential_id: UUID of credential to delete

    Returns:
        - 204 No Content: Credential deleted successfully
        - 404 Not Found: Credential not found
        - 500 Internal Server Error: Delete failed
    """
    correlation_id = _generate_correlation_id()

    try:
        success = delete_credential(credential_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f'Credential not found: {credential_id}',
            )

        logger.info(f'Credential deleted: {credential_id}, correlation_id={correlation_id}')
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Failed to delete credential {credential_id}: {e}, correlation_id={correlation_id}')
        raise HTTPException(
            status_code=500,
            detail='Failed to delete credential',
        )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8002,
        log_level='info',
    )
