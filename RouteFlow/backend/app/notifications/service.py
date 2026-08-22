"""NotificationService: persists notification records and dispatches them.

Design guarantees:
- **Retry-safe / isolated:** a provider failure is captured on the notification
  record (status = FAILED) but never raised to the caller, so an email outage
  cannot roll back an order status change.
- **Auditable:** every attempt is stored with channel, event, status and any
  failure reason.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.enums import (
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
)
from app.models.notification import Notification
from app.notifications.base import NotificationProvider, OutboundMessage
from app.notifications.email import build_email_provider
from app.notifications.sms import build_sms_provider
from app.utils.logging import get_logger

logger = get_logger("notifications.service")

_SUBJECTS = {
    NotificationEvent.ORDER_CONFIRMED: "Your RouteFlow order is confirmed",
    NotificationEvent.AGENT_ASSIGNED: "A delivery agent has been assigned",
    NotificationEvent.PICKED_UP: "Your package has been picked up",
    NotificationEvent.IN_TRANSIT: "Your package is in transit",
    NotificationEvent.OUT_FOR_DELIVERY: "Your package is out for delivery",
    NotificationEvent.DELIVERED: "Your package has been delivered",
    NotificationEvent.FAILED: "Delivery attempt failed",
    NotificationEvent.RESCHEDULED: "Your delivery has been rescheduled",
}

_BODIES = {
    NotificationEvent.ORDER_CONFIRMED: "Order {order} is confirmed. Total: {currency} {total}.",
    NotificationEvent.AGENT_ASSIGNED: "Agent assigned to order {order}. Pickup scheduled soon.",
    NotificationEvent.PICKED_UP: "Order {order} has been picked up by our agent.",
    NotificationEvent.IN_TRANSIT: "Order {order} is now in transit.",
    NotificationEvent.OUT_FOR_DELIVERY: "Order {order} is out for delivery today.",
    NotificationEvent.DELIVERED: "Order {order} has been delivered. Thank you!",
    NotificationEvent.FAILED: "Delivery of order {order} failed ({reason}). You can reschedule from your dashboard.",
    NotificationEvent.RESCHEDULED: "Order {order} has been rescheduled to {date}.",
}


class NotificationService:
    def __init__(
        self,
        db: Session,
        email_provider: Optional[NotificationProvider] = None,
        sms_provider: Optional[NotificationProvider] = None,
    ) -> None:
        self.db = db
        self.email_provider = email_provider or build_email_provider()
        self.sms_provider = sms_provider or build_sms_provider()

    def notify(
        self,
        *,
        order_id: Optional[int],
        order_number: str,
        event: NotificationEvent,
        recipient_email: str,
        recipient_phone: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> None:
        """Send email (always) and SMS (if enabled) for a status event."""
        ctx = {"order": order_number, **(context or {})}
        subject = _SUBJECTS.get(event, "RouteFlow update")
        body = _BODIES.get(event, "Update for order {order}.").format_map(_safe_ctx(ctx))

        self._dispatch(
            order_id=order_id,
            channel=NotificationChannel.EMAIL,
            provider=self.email_provider,
            recipient=recipient_email,
            event=event,
            subject=subject,
            body=body,
        )
        if recipient_phone and self.sms_provider.enabled:
            self._dispatch(
                order_id=order_id,
                channel=NotificationChannel.SMS,
                provider=self.sms_provider,
                recipient=recipient_phone,
                event=event,
                subject=subject,
                body=body,
            )

    def _dispatch(
        self,
        *,
        order_id: Optional[int],
        channel: NotificationChannel,
        provider: NotificationProvider,
        recipient: str,
        event: NotificationEvent,
        subject: str,
        body: str,
    ) -> None:
        record = Notification(
            order_id=order_id,
            recipient=recipient,
            channel=channel,
            event_type=event,
            subject=subject,
            message=body,
            status=NotificationStatus.PENDING,
            attempts=0,
        )
        self.db.add(record)
        self.db.flush()

        if not provider.enabled:
            record.status = NotificationStatus.PENDING
            record.failure_reason = f"{channel.value} provider disabled"
            self.db.flush()
            return

        record.attempts += 1
        try:
            provider.send(OutboundMessage(recipient=recipient, subject=subject, body=body))
            record.status = NotificationStatus.SENT
            record.sent_at = datetime.now(timezone.utc)
        except Exception as exc:  # isolated on purpose — never break the order flow
            record.status = NotificationStatus.FAILED
            record.failure_reason = str(exc)[:500]
            logger.warning(
                "notification_failed",
                extra={"extra_fields": {"channel": channel.value, "event": event.value}},
            )
        finally:
            self.db.flush()


def _safe_ctx(ctx: dict) -> dict:
    """Provide default blanks so ``str.format`` never raises on missing keys."""
    from collections import defaultdict

    d: dict = defaultdict(str)
    d.update(ctx)
    return d
