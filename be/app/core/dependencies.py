from typing import List
from uuid import UUID
from fastapi import Depends, Request
# pyrefly: ignore [missing-import]
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.core.enums import MembershipRole, MembershipStatus
from app.shared.exceptions import AuthenticationException, AuthorizationException
from app.core.security import security_manager
from app.auth.repository import UserRepository
from app.auth.model import User


async def get_db() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency yielding the active MongoDB Motor database instance.
    Guarantees operations flow through the managed connection pool.
    """
    return get_database()



async def get_current_user(
    request: Request,
    user_repo: UserRepository = Depends(lambda: UserRepository()),
) -> User:
    """
    FastAPI dependency validating the JWT access token and resolving the caller's User document.

    Raises:
        AuthenticationException: If token is missing, invalid, expired, or has been revoked.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationException("Missing or invalid authorization credentials")

    token = auth_header.split(" ")[1]

    # Validate access token claims and signature
    claims = security_manager.validate_access_token(token)

    user_id_str = claims.get("uid")
    tv = claims.get("tv")
    if not user_id_str or tv is None:
        raise AuthenticationException("Invalid authentication credentials")

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise AuthenticationException("Invalid authentication credentials")

    # Fetch user details
    user = await user_repo.get_by_id(user_id)
    if not user or user.is_deleted:
        raise AuthenticationException("User account not found")

    # Enforce global token revocation version check
    if user.token_version > tv:
        raise AuthenticationException("Authentication token has been revoked")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency verifying that the currently authenticated user's account is active.
    """
    if not current_user.is_active:
        raise AuthenticationException("User account is inactive")
    return current_user


async def get_current_user_id(
    current_user: User = Depends(get_current_active_user),
) -> UUID:
    """
    Wrapper dependency returning the active user's UUID.
    """
    return current_user.user_id


class PermissionChecker:
    """
    FastAPI dependency builder verifying user membership and roles inside a tenant company workspace.
    """

    def __init__(self, allowed_roles: List[MembershipRole]) -> None:
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        request: Request,
        user_id: UUID = Depends(get_current_user_id),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ) -> dict:
        """
        Intercepts the request to parse X-Company-ID and evaluate tenant RBAC rules.
        """
        company_id_str = request.headers.get("X-Company-ID")
        if not company_id_str:
            raise AuthorizationException(
                "Header X-Company-ID is required for workspace operations"
            )

        try:
            company_id = UUID(company_id_str)
        except ValueError:
            raise AuthorizationException("Invalid workspace ID format")

        # TODO: Query the company_members collection using the database reference to verify:
        # 1. User has an active membership: company_members.status == MembershipStatus.ACTIVE
        # 2. User's role matches: company_members.role IN self.allowed_roles
        # 3. Soft-delete check: company_members.is_deleted == False

        # Temporary mock context representing a valid membership resolver
        return {
            "user_id": user_id,
            "company_id": company_id,
            "role": MembershipRole.ADMIN,
            "status": MembershipStatus.ACTIVE,
        }

