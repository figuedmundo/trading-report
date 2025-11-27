"""
Pydantic models for credential service request/response validation.

Defines request models for credential operations and standardized response models.
All responses include correlation_id for distributed tracing.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from uuid import UUID


# Request Models

class CredentialRequest(BaseModel):
    """Request model for creating or updating credentials."""

    model_config = ConfigDict(populate_by_name=True)

    domain: str = Field(..., min_length=3, max_length=255, description='Portal domain (e.g., broker.com)')
    username: str = Field(..., min_length=1, max_length=255, description='Portal username')
    password: str = Field(..., min_length=1, description='Portal password')
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description='Portal-specific metadata (login URLs, form selectors, 2FA settings)'
    )

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Validate domain format."""
        # Basic domain validation
        if not v or len(v) < 3:
            raise ValueError('Domain must be at least 3 characters')
        if ' ' in v:
            raise ValueError('Domain cannot contain spaces')
        return v.lower()

    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        """Validate password minimum length."""
        if len(v) < 1:
            raise ValueError('Password cannot be empty')
        return v


# Response Models

class CredentialResponse(BaseModel):
    """Response model for credential retrieval/creation/update."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID = Field(..., description='Unique credential identifier')
    domain: str = Field(..., description='Portal domain')
    username: str = Field(..., description='Portal username')
    password: Optional[str] = Field(None, description='Decrypted password (only in GET requests)')
    metadata: Dict[str, Any] = Field(default_factory=dict, description='Portal-specific metadata')
    is_active: bool = Field(default=True, description='Whether credential is active')
    last_used_at: Optional[datetime] = Field(None, description='Timestamp of last credential retrieval')
    created_at: datetime = Field(..., description='Timestamp when credential was created')
    updated_at: datetime = Field(..., description='Timestamp when credential was last modified')
    correlation_id: Optional[str] = Field(None, description='Correlation ID for distributed tracing')


class CredentialListResponse(BaseModel):
    """Response model for listing credentials."""

    model_config = ConfigDict(populate_by_name=True)

    credentials: List[CredentialResponse] = Field(default_factory=list, description='List of credentials')
    total: int = Field(default=0, description='Total number of credentials')
    correlation_id: Optional[str] = Field(None, description='Correlation ID for distributed tracing')


class ErrorResponse(BaseModel):
    """Error response model."""

    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(..., description='Error code (e.g., CREDENTIAL_NOT_FOUND)')
    message: str = Field(..., description='Human-readable error message')
    details: Optional[Dict[str, Any]] = Field(None, description='Additional error details')
    correlation_id: Optional[str] = Field(None, description='Correlation ID for distributed tracing')


class HealthResponse(BaseModel):
    """Health check response model."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(..., pattern='^(ok|unavailable)$', description='Service status')
    database_connected: bool = Field(..., description='Whether database is connected')
    timestamp: datetime = Field(..., description='Response timestamp')
    correlation_id: Optional[str] = Field(None, description='Correlation ID for distributed tracing')
