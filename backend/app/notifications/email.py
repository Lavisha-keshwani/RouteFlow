"""Email notification providers."""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from app.core.config import settings
from app.domain.enums import NotificationChannel
from app.notifications.base import NotificationProvider, OutboundMessage
from app.utils.logging import get_logger

logger = get_logger("notifications.email")


class ConsoleEmailProvider(NotificationProvider):
    """Development provider that logs the email instead of sending it."""

    channel = NotificationChannel.EMAIL

    @property
    def enabled(self) -> bool:
        return settings.EMAIL_ENABLED

    def send(self, message: OutboundMessage) -> None:
        logger.info(
            "EMAIL -> %s | %s | %s",
            message.recipient,
            message.subject,
            message.body,
        )


class SMTPEmailProvider(NotificationProvider):
    """SMTP-backed email provider (e.g. Gmail app password, Mailtrap, SES)."""

    channel = NotificationChannel.EMAIL

    @property
    def enabled(self) -> bool:
        return settings.EMAIL_ENABLED and bool(settings.SMTP_HOST)

    def send(self, message: OutboundMessage) -> None:
        msg = MIMEText(message.body)
        msg["Subject"] = message.subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = message.recipient

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, [message.recipient], msg.as_string())


def build_email_provider() -> NotificationProvider:
    """Select the email provider based on configuration."""
    if settings.EMAIL_PROVIDER == "smtp" and settings.SMTP_HOST:
        return SMTPEmailProvider()
    return ConsoleEmailProvider()
