import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

import aiosmtplib

from app.core.config import get_settings

logger = logging.getLogger("supportai.notification")


class NotificationProvider(Protocol):
    """
    Interface for dispatching system notifications (e.g. email OTP verification).
    """

    async def send_email_otp(self, email: str, otp: str) -> None:
        """
        Sends a 6-digit OTP code to the user's email for verification.
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
    Used when no SMTP credentials are configured.
    """

    async def send_email_otp(self, email: str, otp: str) -> None:
        logger.info(
            f"[MOCK EMAIL] Verification OTP sent to {email}. "
            f"OTP Code: {otp}"
        )

    async def send_password_reset(self, email: str, token: str) -> None:
        settings = get_settings()
        url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        logger.info(
            f"[MOCK EMAIL] Password reset email sent to {email}. "
            f"Reset URL: {url}"
        )


class SmtpNotificationProvider:
    """
    Real SMTP email provider using aiosmtplib.
    Reads configuration from app settings.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    async def _send(self, to_email: str, subject: str, html_body: str) -> None:
        """Send an HTML email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self._settings.SMTP_FROM_NAME} <{self._settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._settings.SMTP_HOST,
                port=self._settings.SMTP_PORT,
                username=self._settings.SMTP_USERNAME,
                password=self._settings.SMTP_PASSWORD,
                start_tls=self._settings.SMTP_USE_TLS,
            )
            logger.info(f"[SMTP] Email '{subject}' sent successfully to {to_email}")
        except Exception as exc:
            logger.error(f"[SMTP] Failed to send email to {to_email}: {exc}", exc_info=True)
            raise

    async def send_email_otp(self, email: str, otp: str) -> None:
        subject = "Your SupportAI verification code"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background: #f4f4f7; padding: 40px 0;">
          <div style="max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 8px;
                      padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <h1 style="color: #1a1a2e; font-size: 24px; margin-bottom: 8px;">
              Welcome to SupportAI 👋
            </h1>
            <p style="color: #555; font-size: 15px; line-height: 1.6;">
              Thanks for signing up! Use the verification code below to activate your account.
              This code expires in <strong>10 minutes</strong>.
            </p>
            <div style="text-align: center; margin: 32px 0;">
              <div style="display: inline-block; background: #f3f0ff; border: 2px dashed #7c3aed;
                          border-radius: 12px; padding: 20px 40px;">
                <span style="font-size: 40px; font-weight: 800; letter-spacing: 12px;
                             color: #7c3aed; font-family: monospace;">{otp}</span>
              </div>
            </div>
            <p style="color: #888; font-size: 13px; line-height: 1.6; text-align: center;">
              Enter this code on the verification page. Do not share this code with anyone.
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
            <p style="color: #aaa; font-size: 12px; text-align: center;">
              If you didn't create a SupportAI account, you can safely ignore this email.
            </p>
          </div>
        </body>
        </html>
        """
        await self._send(email, subject, html_body)

    async def send_password_reset(self, email: str, token: str) -> None:
        settings = self._settings
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        subject = "Reset your SupportAI password"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background: #f4f4f7; padding: 40px 0;">
          <div style="max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 8px;
                      padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <h1 style="color: #1a1a2e; font-size: 24px; margin-bottom: 8px;">
              Reset your password 🔑
            </h1>
            <p style="color: #555; font-size: 15px; line-height: 1.6;">
              We received a request to reset your password. Click the button below to choose a new one.
              This link expires in <strong>1 hour</strong>.
            </p>
            <div style="text-align: center; margin: 32px 0;">
              <a href="{reset_url}"
                 style="background: #7c3aed; color: #ffffff; text-decoration: none;
                        padding: 14px 32px; border-radius: 6px; font-size: 15px;
                        font-weight: 600; display: inline-block;">
                Reset Password
              </a>
            </div>
            <p style="color: #888; font-size: 13px; line-height: 1.6;">
              If the button doesn't work, copy and paste this URL into your browser:<br/>
              <a href="{reset_url}" style="color: #7c3aed; word-break: break-all;">{reset_url}</a>
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
            <p style="color: #aaa; font-size: 12px; text-align: center;">
              If you didn't request a password reset, you can safely ignore this email.
            </p>
          </div>
        </body>
        </html>
        """
        await self._send(email, subject, html_body)


def get_notification_provider() -> "SmtpNotificationProvider | MockNotificationProvider":
    """
    Factory that returns the real SMTP provider if credentials are configured,
    otherwise falls back to the mock provider.
    """
    settings = get_settings()
    if settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
        logger.info("[Notification] Using SmtpNotificationProvider")
        return SmtpNotificationProvider()
    logger.warning(
        "[Notification] SMTP not configured — using MockNotificationProvider. "
        "Emails will only be logged to console."
    )
    return MockNotificationProvider()
