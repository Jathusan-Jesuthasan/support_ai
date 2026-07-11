import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from uuid import UUID
# pyrefly: ignore [missing-import]
import jwt
from app.core.config import get_settings
from app.shared.exceptions import AuthenticationException, TokenExpiredException


class JwtManager:
    """
    Manages JSON Web Token (JWT) lifecycles under RFC 7519.
    Handles token creation, claim extraction, and signature validation.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

        # Secret key & signing algorithm
        self._secret_key = str(self._settings.JWT_SECRET_KEY)
        self._algorithm = self._settings.JWT_ALGORITHM

        # Standard claims default fallbacks
        self._issuer = "supportai"
        self._audience = "supportai"

        # Expiry bounds
        self._access_expiry = timedelta(minutes=self._settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self._refresh_expiry = timedelta(days=self._settings.REFRESH_TOKEN_EXPIRE_DAYS)

    def create_access_token(
        self,
        user_id: UUID,
        session_id: UUID,
        token_version: int,
    ) -> str:
        """
        Generates a short-lived access JWT containing user identities.
        Claims: sub, uid, sid, tv, iat, nbf, exp, iss, aud, jti
        """
        now = datetime.now(timezone.utc)
        payload = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": f"usr_{user_id}",
            "uid": str(user_id),
            "sid": str(session_id),
            "tv": token_version,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int((now + self._access_expiry).timestamp()),
            "jti": str(uuid.uuid4()),
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(
        self,
        user_id: UUID,
        session_id: UUID,
        token_version: int,
    ) -> str:
        """
        Generates a long-lived refresh JWT used to rotate access tokens.
        Claims: sub, uid, sid, tv, iat, exp, jti
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": f"usr_{user_id}",
            "uid": str(user_id),
            "sid": str(session_id),
            "tv": token_version,
            "iat": int(now.timestamp()),
            "exp": int((now + self._refresh_expiry).timestamp()),
            "jti": str(uuid.uuid4()),
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str, verify_aud_iss: bool = True) -> Dict[str, Any]:
        """
        Decodes and verifies a JWT signature, validating core claims.

        Args:
            token: The raw JWT string to decode.
            verify_aud_iss: If True, validates aud and iss claims (required for Access, omitted for Refresh).

        Raises:
            TokenExpiredException: If the token expiration time is passed.
            AuthenticationException: If signature validation or claim matching fails.
        """
        try:
            options: Dict[str, Any] = {}
            if not verify_aud_iss:
                options["verify_aud"] = False
                options["verify_iss"] = False

            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                audience=self._audience if verify_aud_iss else None,
                issuer=self._issuer if verify_aud_iss else None,
                options=options,
                leeway=10,  # 10 seconds clock skew tolerance
            )
            return payload
        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredException("Authentication token has expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationException("Invalid authentication credentials") from e


# Expose a default instance for singleton consumption
jwt_manager = JwtManager()
