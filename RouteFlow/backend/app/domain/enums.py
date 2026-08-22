"""Domain enumerations shared across models, schemas and services.

Centralising enums keeps the state machine, rate engine and API contracts in
sync and avoids magic strings scattered through the codebase.
"""
from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    DELIVERY_AGENT = "DELIVERY_AGENT"
    ADMIN = "ADMIN"


class OrderType(str, enum.Enum):
    B2B = "B2B"
    B2C = "B2C"


class PaymentType(str, enum.Enum):
    PREPAID = "PREPAID"
    COD = "COD"


class ZoneType(str, enum.Enum):
    INTRA_ZONE = "INTRA_ZONE"
    INTER_ZONE = "INTER_ZONE"


class OrderStatus(str, enum.Enum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED = "CANCELLED"


class AgentStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class DeliveryAttemptStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class FailureReason(str, enum.Enum):
    CUSTOMER_UNAVAILABLE = "CUSTOMER_UNAVAILABLE"
    WRONG_ADDRESS = "WRONG_ADDRESS"
    CUSTOMER_REFUSED = "CUSTOMER_REFUSED"
    DAMAGED_PACKAGE = "DAMAGED_PACKAGE"
    OTHER = "OTHER"


class NotificationChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationEvent(str, enum.Enum):
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    AGENT_ASSIGNED = "AGENT_ASSIGNED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RESCHEDULED = "RESCHEDULED"
