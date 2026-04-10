from __future__ import annotations

import logging

from app.config import Settings

logger = logging.getLogger(__name__)


def _make_verification_link(token: str, app_base_url: str) -> str:
    return f"{app_base_url}?verify_token={token}"


def _make_reset_link(token: str, app_base_url: str) -> str:
    return f"{app_base_url}?reset_token={token}"


async def send_verification_email(to_email: str, token: str, settings: Settings) -> None:
    link = _make_verification_link(token, settings.app_base_url)

    if not settings.smtp_host:
        logger.info(
            "SMTP not configured — email verification link for %s: %s",
            to_email,
            link,
        )
        return

    await _send_email(
        to_email=to_email,
        subject="Verify your Flight Tracker email",
        body=(
            f"Hi,\n\n"
            f"Please verify your email address by clicking the link below:\n\n"
            f"{link}\n\n"
            f"This link expires in 24 hours.\n\n"
            f"If you did not create an account, you can safely ignore this email."
        ),
        settings=settings,
    )


async def send_password_reset_email(to_email: str, token: str, settings: Settings) -> None:
    link = _make_reset_link(token, settings.app_base_url)

    if not settings.smtp_host:
        logger.info(
            "SMTP not configured — password reset link for %s: %s",
            to_email,
            link,
        )
        return

    await _send_email(
        to_email=to_email,
        subject="Reset your Flight Tracker password",
        body=(
            f"Hi,\n\n"
            f"You requested a password reset. Click the link below to set a new password:\n\n"
            f"{link}\n\n"
            f"This link expires in 1 hour.\n\n"
            f"If you did not request this, you can safely ignore this email."
        ),
        settings=settings,
    )


async def _send_email(to_email: str, subject: str, body: str, settings: Settings) -> None:
    try:
        import aiosmtplib
        from email.mime.text import MIMEText

        message = MIMEText(body, "plain")
        message["From"] = settings.smtp_from_email
        message["To"] = to_email
        message["Subject"] = subject

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            start_tls=True,
        )
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
