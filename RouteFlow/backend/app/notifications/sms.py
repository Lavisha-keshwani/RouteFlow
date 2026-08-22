"""SMS notification providers (behind an abstraction, disabled by default).

The application works fully without SMS credentials — when disabled the provider
simply reports itself as unavailable and the SMS channel is skipped.
"""
from __future__ import annotations

from app.core.config import settings
from app.domain.enums import NotificationChannel
from app.notifications.base import NotificationProvider, OutboundMessage
from app.utils.logging import get_logger

logger = get_logger("notifications.sms")


class ConsoleSMSProvider(NotificationProvider):
    """Development SMS provider that logs the message."""

    channel = NotificationChannel.SMS

    @property
    def enabled(self) -> bool:
        return settings.SMS_ENABLED

    def send(self, message: OutboundMessage) -> None:
        logger.info("SMS -> %s | %s", message.recipient, message.body)


class TwilioSMSProvider(NotificationProvider):
    """Placeholder Twilio provider wired through environment configuration.

    Kept behind the abstraction so real credentials can be added without any
    changes to calling code.
    """

    channel = NotificationChannel.SMS

    @property
    def enabled(self) -> bool:
        return settings.SMS_ENABLED and bool(settings.SMS_API_KEY)

    def send(self, message: OutboundMessage) -> None:  # pragma: no cover
        # Real implementation would call Twilio's REST API here using httpx.
        logger.info("SMS(twilio) -> %s | %s", message.recipient, message.body)


def build_sms_provider() -> NotificationProvider:
    """Select the SMS provider based on configuration."""
    if settings.SMS_PROVIDER == "twilio" and settings.SMS_API_KEY:
        return TwilioSMSProvider()
    return ConsoleSMSProvider()
