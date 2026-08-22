"""Notification provider abstraction.

Providers are intentionally simple and side-effect isolated: a failure to send
must never propagate out and roll back an order status change. The
NotificationService records the outcome; providers only attempt delivery.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass

from app.domain.enums import NotificationChannel


@dataclass
class OutboundMessage:
    recipient: str
    subject: str
    body: str


class NotificationProvider(abc.ABC):
    """Base class for a single-channel notification provider."""

    channel: NotificationChannel

    @property
    @abc.abstractmethod
    def enabled(self) -> bool:
        """Whether this provider is configured and should attempt delivery."""

    @abc.abstractmethod
    def send(self, message: OutboundMessage) -> None:
        """Attempt delivery. Raise on failure so the caller can record it."""
