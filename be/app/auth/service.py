import hashlib
import logging
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from app.core.config import get_settings
from app.core.jwt import JwtManager, jwt_manager
from app.core.password import PasswordManager
from app.notification.provider import NotificationProvider, MockNotificationProvider, get_notification_provider
from app.auth.model import User, VerificationToken, Session, TokenPurpose
from app.auth.repository import UserRepository, VerificationTokenRepository, SessionRepository
from app.auth.schema import (
    UserSignupRequest,
    UserLoginRequest,
    TokenResponseData,
    UserMeResponseData,
)
from app.shared.exceptions import (
    DuplicateResourceException,
    AuthenticationException,
    SessionExpiredException,
    BadRequestException,
    TokenExpiredException,
)

logger = logging.getLogger("supportai.auth")


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AuthService:
    """
    Coordinates password validation, JWT generation, session management,
    and database operations to enforce auth business logic.
    """

    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        token_repo: Optional[VerificationTokenRepository] = None,
        session_repo: Optional[SessionRepository] = None,
        password_mgr: Optional[PasswordManager] = None,
        jwt_mgr: Optional[JwtManager] = None,
        notification_provider: Optional[NotificationProvider] = None,
    ) -> None:
        self._user_repo = user_repo or UserRepository()
        self._token_repo = token_repo or VerificationTokenRepository()
        self._session_repo = session_repo or SessionRepository()
        self._password_mgr = password_mgr or PasswordManager()
        self._jwt_mgr = jwt_mgr or jwt_manager
        self._notification_provider = notification_provider or get_notification_provider()
        self._settings = get_settings()

    async def signup(self, request: UserSignupRequest) -> User:
        """
        Registers a new user, hashes their password, and creates an email verification token.
        """
        # 1. Normalize email
        email = request.email.strip().lower()

        # 2. Validate password strength
        self._password_mgr.validate_password_strength(request.password)

        # 3. Check for existing email address
        existing_user = await self._user_repo.get_by_email(email)
        if existing_user:
            raise DuplicateResourceException("Email address is already registered")

        # 4. Hash password
        hashed_password = self._password_mgr.hash_password(request.password)

        # 5. Create user entity
        now = datetime.now(timezone.utc)
        user = User(
            user_id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            full_name=request.full_name,
            is_active=False,  # inactive until email is verified
            is_email_verified=False,
            token_version=1,
            failed_login_attempts=0,
            locked_until=None,
            created_at=now,
            updated_at=now,
        )
        await self._user_repo.create(user)

        # 6. Generate 6-digit OTP
        otp = f"{random.randint(0, 999999):06d}"
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        expires_at = now + timedelta(minutes=10)

        v_token = VerificationToken(
            token_id=uuid.uuid4(),
            user_id=user.user_id,
            token_hash=otp_hash,
            purpose=TokenPurpose.EMAIL_VERIFICATION,
            expires_at=expires_at,
            created_at=now,
        )
        await self._token_repo.create(v_token)

        # 7. Dispatch OTP email (non-fatal — log error if SMTP fails)
        try:
            await self._notification_provider.send_email_otp(email, otp)
        except Exception as email_exc:
            logger.error(
                f"Failed to send OTP email to {email}: {email_exc}. "
                f"User created but email not sent. OTP: {otp}",
                exc_info=True,
            )

        return user

    async def verify_email_otp(self, email: str, otp: str) -> None:
        """
        Verifies a user's email using the 6-digit OTP they entered.
        """
        email = email.strip().lower()
        user = await self._user_repo.get_by_email(email)
        if not user:
            raise BadRequestException("No account found for this email address")

        if user.is_email_verified:
            raise BadRequestException("This email address is already verified")

        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        token = await self._token_repo.get_by_hash(otp_hash, TokenPurpose.EMAIL_VERIFICATION)

        # Validate: token exists, belongs to user, unused, not expired
        now = datetime.now(timezone.utc)
        expires_at = _ensure_utc(token.expires_at) if token else None
        if (
            not token
            or token.user_id != user.user_id
            or token.used_at is not None
            or (expires_at is not None and expires_at < now)
        ):
            raise BadRequestException("Invalid or expired verification code")

        # Activate user
        user.is_email_verified = True
        user.is_active = True
        user.updated_at = now
        await self._user_repo.update(user)

        # Mark token as used
        token.used_at = now
        await self._token_repo.update(token)

    async def resend_verification_otp(self, email: str) -> None:
        """
        Invalidates any existing OTP tokens for the user and sends a fresh 6-digit OTP.
        """
        email = email.strip().lower()
        user = await self._user_repo.get_by_email(email)
        if not user:
            # Return silently to avoid user-enumeration attacks
            return

        if user.is_email_verified:
            raise BadRequestException("This email address is already verified")

        now = datetime.now(timezone.utc)

        # Generate new OTP
        otp = f"{random.randint(0, 999999):06d}"
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        expires_at = now + timedelta(minutes=10)

        v_token = VerificationToken(
            token_id=uuid.uuid4(),
            user_id=user.user_id,
            token_hash=otp_hash,
            purpose=TokenPurpose.EMAIL_VERIFICATION,
            expires_at=expires_at,
            created_at=now,
        )
        await self._token_repo.create(v_token)

        try:
            await self._notification_provider.send_email_otp(email, otp)
        except Exception as email_exc:
            logger.error(
                f"Failed to resend OTP to {email}: {email_exc}. OTP: {otp}",
                exc_info=True,
            )

    async def login(self, request: UserLoginRequest, ip: Optional[str], ua: Optional[str]) -> TokenResponseData:
        """
        Authenticates credentials, manages failed attempt limits, and issues access/refresh tokens.
        """
        email = request.email.strip().lower()
        user = await self._user_repo.get_by_email(email)

        if not user or user.is_deleted:
            raise AuthenticationException("Invalid email or password")

        if not user.is_active:
            raise AuthenticationException("User account is inactive or email is unverified")

        now = datetime.now(timezone.utc)


        # Check account lockout
        locked_until = _ensure_utc(user.locked_until)
        if locked_until and now < locked_until:
            raise AuthenticationException("Account is temporarily locked. Try again in 15 minutes.")


        # Verify password credentials
        is_valid = self._password_mgr.verify_password(request.password, user.hashed_password)
        if not is_valid:
            # Increment failed attempts
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)
                logger.warning(f"Account locked: {email} due to excessive failures.")
            await self._user_repo.update(user)
            raise AuthenticationException("Invalid email or password")

        # Success - Reset lockout counters
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        user.last_login_ip = ip
        user.last_login_user_agent = ua
        user.updated_at = now
        await self._user_repo.update(user)

        # Create session
        session_id = uuid.uuid4()
        expires_at = now + timedelta(days=self._settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Generate tokens
        access_token = self._jwt_mgr.create_access_token(user.user_id, session_id, user.token_version)
        refresh_token = self._jwt_mgr.create_refresh_token(user.user_id, session_id, user.token_version)

        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            ip_address=ip,
            user_agent=ua,
            created_ip=ip,
            is_revoked=False,
            last_seen_at=now,
            last_used_at=now,
            created_at=now,
            updated_at=now,
        )
        await self._session_repo.create(session)

        return TokenResponseData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, refresh_token: str, ip: Optional[str], ua: Optional[str]) -> TokenResponseData:
        """
        Performs OAuth 2.1 Refresh Token Rotation and handles replay protection attacks.
        """
        try:
            claims = self._jwt_mgr.decode_token(refresh_token, verify_aud_iss=False)
        except TokenExpiredException as e:
            raise SessionExpiredException("Refresh token has expired") from e
        except AuthenticationException as e:
            raise SessionExpiredException("Invalid refresh token") from e

        user_id = UUID(claims["uid"])
        session_id = UUID(claims["sid"])


        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        session = await self._session_repo.get_by_id(session_id)

        if not session:
            raise AuthenticationException("Invalid session context")

        now = datetime.now(timezone.utc)

        # 1. Replay attack check: If the token presented does not match the active hash of the session
        if session.refresh_token_hash != token_hash:
            logger.critical(f"TOKEN_REPLAY_DETECTED for user {user_id} on session {session_id}!")
            
            # Revoke all sessions for this user immediately
            await self._session_repo.revoke_all_for_user(user_id)

            # Increment user's token version globally to invalidate all existing access tokens
            user = await self._user_repo.get_by_id(user_id)
            if user:
                user.token_version += 1
                user.updated_at = now
                await self._user_repo.update(user)

            raise AuthenticationException("Authentication refresh failed due to token reuse detection.")

        # 2. Expiry or Revocation check
        expires_at = _ensure_utc(session.expires_at)
        if session.is_revoked or (expires_at is not None and expires_at < now):
            raise SessionExpiredException("Session is revoked or expired")



        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.is_active or user.is_deleted:
            raise AuthenticationException("User is suspended or deleted")

        # 3. Rotate tokens
        new_access_token = self._jwt_mgr.create_access_token(user_id, session_id, user.token_version)
        new_refresh_token = self._jwt_mgr.create_refresh_token(user_id, session_id, user.token_version)

        new_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()

        # Update session
        session.refresh_token_hash = new_hash
        session.last_used_at = now
        session.last_seen_at = now
        session.ip_address = ip
        session.user_agent = ua
        session.updated_at = now
        await self._session_repo.update(session)

        return TokenResponseData(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=self._settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token: str) -> None:
        """
        Logs out a single session by revoking the refresh token hash.
        """
        try:
            claims = self._jwt_mgr.decode_token(refresh_token, verify_aud_iss=False)
        except Exception:
            # If decoding fails (e.g. token expired), we swallow it and continue
            return

        session_id = UUID(claims["sid"])
        await self._session_repo.revoke_by_id(session_id)

    async def get_me(self, user_id: UUID) -> UserMeResponseData:
        """
        Retrieves user profile information for a valid session.
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.is_active or user.is_deleted:
            raise AuthenticationException("User profile is unavailable")

        return UserMeResponseData(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            active_company=None,  # Handled in Sprint 4
            created_at=user.created_at,
        )
