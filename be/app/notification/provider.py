import logging
from typing import Protocol

logger = logging.getLogger("supportai.notification")


class NotificationProvider(Protocol):
    """
    Interface for dispatching system notifications (e.g. email verification).
    """

    async def send_email_verification(self, email: str, token: str) -> None:
        """
        Sends email verification link containing the verification token.
        """
        ...

    async def send_password_reset(self, email: str, token: str) -> None:
        """
        Sends password reset link containing the reset token.
        """
        ...


class MockNotificationProvider:
    """
    Mock implementation that logs notifications to console/files.
    """

    async def send_email_verification(self, email: str, token: str) -> None:
        logger.info(
            f"[MOCK EMAIL] Verification email sent to {email}. "
            f"Verification URL: http://127.0.0.1:8001/api/v1/auth/verify-email?token={token}"
        )

    async def send_password_reset(self, email: str, token: str) -> None:
        logger.info(
            f"[MOCK EMAIL] Password reset email sent to {email}. "
            f"Reset Token: {token}"
        )
