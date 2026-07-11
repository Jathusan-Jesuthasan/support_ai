from fastapi import APIRouter, Depends, Request, status, Query
from app.auth.schema import (
    UserSignupRequest,
    UserSignupResponse,
    UserLoginRequest,
    UserLoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserLogoutRequest,
    UserLogoutResponse,
    UserMeResponse,
    VerifyEmailResponse,
    UserResponseData,
)
from app.auth.service import AuthService
from app.auth.model import User
from app.core.dependencies import get_current_active_user

router = APIRouter()


def get_auth_service() -> AuthService:
    """
    FastAPI dependency yielding the active AuthService instance.
    """
    return AuthService()


@router.post("/signup", response_model=UserSignupResponse, status_code=status.HTTP_201_CREATED, summary="Create a new user")
async def signup(request_payload: UserSignupRequest, service: AuthService = Depends(get_auth_service)):
    """
    Registers a new user, hashes their credentials, and sends an email verification link.
    """
    user = await service.signup(request_payload)
    return UserSignupResponse(
        status="success",
        data=UserResponseData(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            is_email_verified=user.is_email_verified,
            created_at=user.created_at,
        ),
    )


@router.get("/verify-email", response_model=VerifyEmailResponse, summary="Verify user email address")
async def verify_email(
    token: str = Query(..., description="The unique verification token sent to the user's email"),
    service: AuthService = Depends(get_auth_service)
):
    """
    Confirms email address ownership using the verification token and activates the account.
    """
    await service.verify_email(token)
    return VerifyEmailResponse()


@router.post("/login", response_model=UserLoginResponse, summary="Authenticate user and create session")
async def login(
    request: Request,
    request_payload: UserLoginRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Verifies user credentials, increments failure counts on mismatch, and generates an access/refresh token pair.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    tokens = await service.login(request_payload, ip_address, user_agent)
    return UserLoginResponse(status="success", data=tokens)


@router.post("/refresh", response_model=TokenRefreshResponse, summary="Rotate refresh token session")
async def refresh(
    request: Request,
    request_payload: TokenRefreshRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Uses a valid, unused refresh token to rotate credentials, updating session details.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    tokens = await service.refresh(request_payload.refresh_token, ip_address, user_agent)
    return TokenRefreshResponse(status="success", data=tokens)


@router.post("/logout", response_model=UserLogoutResponse, summary="Revoke current session")
async def logout(request_payload: UserLogoutRequest, service: AuthService = Depends(get_auth_service)):
    """
    Revokes the active refresh token session, preventing any subsequent refreshes.
    """
    await service.logout(request_payload.refresh_token)
    return UserLogoutResponse()


@router.get("/me", response_model=UserMeResponse, summary="Get active user profile details")
async def get_me(
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service)
):
    """
    Retrieves the identity profile for the currently authorized user session.
    """
    profile = await service.get_me(current_user.user_id)
    return UserMeResponse(status="success", data=profile)
