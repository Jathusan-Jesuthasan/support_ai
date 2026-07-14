from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# =====================================================================
# Request Schemas
# =====================================================================

class UserSignupRequest(BaseModel):
    email: EmailStr = Field(..., description="The user's email address")
    password: str = Field(..., description="The user's password")
    full_name: str = Field(..., description="The user's full name")


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="The user's registered email address")
    password: str = Field(..., description="The user's password")


class VerifyEmailOtpRequest(BaseModel):
    email: EmailStr = Field(..., description="The email address to verify")
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$", description="The 6-digit OTP sent to the user's email")


class ResendOtpRequest(BaseModel):
    email: EmailStr = Field(..., description="The email address to resend the OTP to")


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="The active refresh token to rotate")


class UserLogoutRequest(BaseModel):
    refresh_token: str = Field(..., description="The active refresh token to revoke")


# =====================================================================
# Response Data Blocks
# =====================================================================

class UserResponseData(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    is_email_verified: bool
    created_at: datetime


class TokenResponseData(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class ActiveCompanyResponse(BaseModel):
    company_id: UUID
    role: str
    status: str


class UserMeResponseData(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    is_active: bool
    active_company: Optional[ActiveCompanyResponse] = None
    created_at: datetime


# =====================================================================
# Envelope Responses (Wrappers)
# =====================================================================

class UserSignupResponse(BaseModel):
    status: str = "success"
    data: UserResponseData


class UserLoginResponse(BaseModel):
    status: str = "success"
    data: TokenResponseData


class TokenRefreshResponse(BaseModel):
    status: str = "success"
    data: TokenResponseData


class UserLogoutResponse(BaseModel):
    status: str = "success"
    message: str = "Session successfully revoked"


class UserMeResponse(BaseModel):
    status: str = "success"
    data: UserMeResponseData


class VerifyEmailResponse(BaseModel):
    status: str = "success"
    message: str = "Email successfully verified. Account is now active."


class ResendOtpResponse(BaseModel):
    status: str = "success"
    message: str = "A new verification code has been sent to your email."
