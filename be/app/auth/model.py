from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import Field
from app.shared.base_model import MongoDocument, BaseEntity, AuditFields


class TokenPurpose(str, Enum):
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    PASSWORD_RESET = "PASSWORD_RESET"


class User(BaseEntity):
    """
    Represents a system user identity document in MongoDB.
    """
    user_id: UUID = Field(..., description="Unique business UUID identifier for the user")
    email: str = Field(..., description="Normalized lowercase unique email address")
    hashed_password: str = Field(..., description="Secure hashed password string")
    full_name: str = Field(..., description="User's full display name")
    is_active: bool = Field(True, description="Flag indicating if the user account is active")
    is_email_verified: bool = Field(False, description="Flag indicating if the user has verified their email")
    token_version: int = Field(1, description="Token version for instant global revocation")
    failed_login_attempts: int = Field(0, description="Counter for consecutive failed login attempts")
    locked_until: Optional[datetime] = Field(None, description="Timestamp until which the account is locked")
    last_login_at: Optional[datetime] = Field(None, description="Timestamp of the last successful login")
    last_login_ip: Optional[str] = Field(None, description="IP address of the last successful login")
    last_login_user_agent: Optional[str] = Field(None, description="User agent of the last successful login")


class VerificationToken(MongoDocument):
    """
    Represents a verification token document for email confirmation or password reset.
    """
    token_id: UUID = Field(..., description="Unique business UUID identifier for the token")
    user_id: UUID = Field(..., description="UUID of the user this token belongs to")
    token_hash: str = Field(..., description="SHA-256 hash of the verification token")
    purpose: TokenPurpose = Field(..., description="Purpose of the token (EMAIL_VERIFICATION or PASSWORD_RESET)")
    expires_at: datetime = Field(..., description="UTC expiration timestamp")
    used_at: Optional[datetime] = Field(None, description="UTC timestamp of when the token was used")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC creation timestamp")


class Session(MongoDocument, AuditFields):
    """
    Represents an active user session for tracking refresh tokens and client contexts.
    """
    session_id: UUID = Field(..., description="Unique business UUID identifier for the session")
    user_id: UUID = Field(..., description="UUID of the user this session belongs to")
    refresh_token_hash: str = Field(..., description="SHA-256 hash of the active refresh token")
    expires_at: datetime = Field(..., description="UTC expiration timestamp of the session")
    ip_address: Optional[str] = Field(None, description="IP address of the current request")
    user_agent: Optional[str] = Field(None, description="User agent of the current request")
    is_revoked: bool = Field(False, description="Flag indicating if the session has been revoked")
    created_ip: Optional[str] = Field(None, description="IP address where the session was initially created")
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of last activity")
    last_used_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of last refresh usage")
