"""Order, Package, DeliveryAttempt and OrderStatusHistory ORM models."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import (
    DeliveryAttemptStatus,
    FailureReason,
    OrderStatus,
    OrderType,
    PaymentType,
    UserRole,
    ZoneType,
)
from app.models.mixins import TimestampMixin


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_status", "status"),
        Index("ix_orders_customer", "customer_id"),
        Index("ix_orders_agent", "assigned_agent_id"),
        Index("ix_orders_pickup_zone", "pickup_zone_id"),
        Index("ix_orders_drop_zone", "drop_zone_id"),
        Index("ix_orders_created_at", "created_at"),
        CheckConstraint("total_charge >= 0", name="ck_order_total_nonneg"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_number: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_agent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("delivery_agents.id", ondelete="SET NULL")
    )

    # Addresses and resolved zones
    pickup_address: Mapped[str] = mapped_column(String(500), nullable=False)
    drop_address: Mapped[str] = mapped_column(String(500), nullable=False)
    pickup_area_id: Mapped[Optional[int]] = mapped_column(ForeignKey("areas.id"))
    drop_area_id: Mapped[Optional[int]] = mapped_column(ForeignKey("areas.id"))
    pickup_zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False)
    drop_zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False)
    pickup_latitude: Mapped[Optional[float]] = mapped_column(Float)
    pickup_longitude: Mapped[Optional[float]] = mapped_column(Float)
    drop_latitude: Mapped[Optional[float]] = mapped_column(Float)
    drop_longitude: Mapped[Optional[float]] = mapped_column(Float)

    # Classification
    order_type: Mapped[OrderType] = mapped_column(
        SQLEnum(OrderType, native_enum=False, length=10), nullable=False
    )
    payment_type: Mapped[PaymentType] = mapped_column(
        SQLEnum(PaymentType, native_enum=False, length=10), nullable=False
    )
    zone_type: Mapped[ZoneType] = mapped_column(
        SQLEnum(ZoneType, native_enum=False, length=15), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, native_enum=False, length=25),
        nullable=False,
        default=OrderStatus.PENDING_CONFIRMATION,
    )

    # --- Immutable pricing snapshot (frozen at confirmation) ---
    chargeable_weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    base_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cod_surcharge: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    total_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    rate_card_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rate_cards.id"))

    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="orders")  # noqa: F821
    assigned_agent: Mapped[Optional["DeliveryAgent"]] = relationship()  # noqa: F821
    pickup_zone: Mapped["Zone"] = relationship(foreign_keys=[pickup_zone_id])  # noqa: F821
    drop_zone: Mapped["Zone"] = relationship(foreign_keys=[drop_zone_id])  # noqa: F821
    package: Mapped[Optional["Package"]] = relationship(
        back_populates="order", uselist=False, cascade="all, delete-orphan"
    )
    attempts: Mapped[List["DeliveryAttempt"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="DeliveryAttempt.attempt_number"
    )
    status_history: Mapped[List["OrderStatusHistory"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at",
    )


class Package(Base, TimestampMixin):
    __tablename__ = "packages"
    __table_args__ = (
        CheckConstraint("length_cm > 0 AND width_cm > 0 AND height_cm > 0", name="ck_pkg_dims_positive"),
        CheckConstraint("actual_weight_kg > 0", name="ck_pkg_actual_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    length_cm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    width_cm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    height_cm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    actual_weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    volumetric_weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    chargeable_weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="package")


class DeliveryAttempt(Base, TimestampMixin):
    """A single delivery attempt. Failed attempts are preserved; rescheduling
    creates a *new* attempt rather than mutating history."""

    __tablename__ = "delivery_attempts"
    __table_args__ = (
        UniqueConstraint("order_id", "attempt_number", name="uq_attempt_order_number"),
        Index("ix_attempts_order", "order_id"),
        Index("ix_attempts_agent", "agent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("delivery_agents.id", ondelete="SET NULL")
    )
    status: Mapped[DeliveryAttemptStatus] = mapped_column(
        SQLEnum(DeliveryAttemptStatus, native_enum=False, length=15),
        nullable=False,
        default=DeliveryAttemptStatus.SCHEDULED,
    )
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date)
    time_window: Mapped[Optional[str]] = mapped_column(String(50))
    failure_reason: Mapped[Optional[FailureReason]] = mapped_column(
        SQLEnum(FailureReason, native_enum=False, length=25)
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    reschedule_reason: Mapped[Optional[str]] = mapped_column(Text)
    assignment_score: Mapped[Optional[float]] = mapped_column(Float)
    assignment_metadata: Mapped[Optional[dict]] = mapped_column(JSON)

    order: Mapped["Order"] = relationship(back_populates="attempts")
    agent: Mapped[Optional["DeliveryAgent"]] = relationship()  # noqa: F821


class OrderStatusHistory(Base):
    """Append-only, immutable tracking history. No update/delete paths exist."""

    __tablename__ = "order_status_history"
    __table_args__ = (Index("ix_status_history_order", "order_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    old_status: Mapped[Optional[OrderStatus]] = mapped_column(
        SQLEnum(OrderStatus, native_enum=False, length=25)
    )
    new_status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, native_enum=False, length=25), nullable=False
    )
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[Optional[UserRole]] = mapped_column(
        SQLEnum(UserRole, native_enum=False, length=20)
    )
    reason: Mapped[Optional[str]] = mapped_column(Text)
    event_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    order: Mapped["Order"] = relationship(back_populates="status_history")
