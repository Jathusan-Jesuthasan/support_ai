from typing import Any, Dict, List, Optional
from uuid import UUID
from app.core.jwt import JwtManager, jwt_manager
from app.core.password import PasswordManager
from app.shared.exceptions import AuthenticationException


class SecurityManager:
    """
    Security orchestrator coordinating credential validation and token claim tracking.
    Enforces unified interfaces for authorization and verification loops.
    """

    def __init__(
        self,
        password_manager: Optional[PasswordManager] = None,
        jwt_mgr: Optional[JwtManager] = None,
    ) -> None:
        self._password_manager = password_manager or PasswordManager()
        self._jwt_manager = jwt_mgr or jwt_manager

    def authenticate_user(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verifies plaintext credentials match the recorded Argon2id password hash.
        """
        return self._password_manager.verify_password(plain_password, hashed_password)

    def get_current_user_claims(self, token: str) -> Dict[str, Any]:
        """
        Decodes a token signature and returns its raw claims context payload.
        """
        return self._jwt_manager.decode_token(token)

    def validate_access_token(self, token: str) -> Dict[str, Any]:
        """
        Decodes a token and strictly validates that it is designated as an ACCESS token
        by checking the presence of standard access claims (iss and aud).
        """
        claims = self._jwt_manager.decode_token(token, verify_aud_iss=True)
        if "iss" not in claims or "aud" not in claims:
            raise AuthenticationException("Invalid token type")
        return claims

    def validate_refresh_token(self, token: str) -> Dict[str, Any]:
        """
        Decodes a token and strictly validates that it is designated as a REFRESH token
        by checking the absence of standard access claims (iss and aud).
        """
        claims = self._jwt_manager.decode_token(token, verify_aud_iss=False)
        if "iss" in claims or "aud" in claims:
            raise AuthenticationException("Invalid token type")
        return claims


    def validate_company_context(self, claims: Dict[str, Any], company_id: UUID) -> bool:
        """
        Validates if the token claim properties match the target company context.
        """
        token_company_id = claims.get("cid")
        if not token_company_id:
            return False
        try:
            return UUID(token_company_id) == company_id
        except ValueError:
            return False

    def validate_role(self, claims: Dict[str, Any], allowed_roles: List[str]) -> bool:
        """
        Checks if the embedded token role matches authorized route permission roles.
        """
        user_role = claims.get("role")
        if not user_role:
            return False
        return user_role in allowed_roles


# Expose a default instance for singleton consumption
security_manager = SecurityManager()
