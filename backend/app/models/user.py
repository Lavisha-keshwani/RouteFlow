"""User, customer and delivery-agent ORM models."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import AgentStatus, UserRole
from app.models.mixins import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False, length=20), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    customer: Mapped[Optional["Customer"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    agent: Mapped[Optional["DeliveryAgent"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    default_pickup_address: Mapped[Optional[str]] = mapped_column(String(500))

    user: Mapped["User"] = relationship(back_populates="customer")
    orders: Mapped[List["Order"]] = relationship(back_populates="customer")  # noqa: F821


class DeliveryAgent(Base, TimestampMixin):
    __tablename__ = "delivery_agents"
    __table_args__ = (
        CheckConstraint("max_active_orders > 0", name="ck_agent_capacity_positive"),
        CheckConstraint("active_orders >= 0", name="ck_agent_active_nonneg"),
        Index("ix_agents_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[AgentStatus] = mapped_column(
        SQLEnum(AgentStatus, native_enum=False, length=20),
        nullable=False,
        default=AgentStatus.OFFLINE,
    )
    current_zone_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("zones.id", ondelete="SET NULL")
    )
    current_latitude: Mapped[Optional[float]] = mapped_column(Float)
    current_longitude: Mapped[Optional[float]] = mapped_column(Float)
    last_location_update: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    max_active_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    active_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped["User"] = relationship(back_populates="agent")
    zone: Mapped[Optional["Zone"]] = relationship()  # noqa: F821
    locations: Mapped[List["AgentLocation"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )

    @property
    def has_capacity(self) -> bool:
        return self.active_orders < self.max_active_orders

    @property
    def is_assignable(self) -> bool:
        return (
            self.is_active
            and self.status == AgentStatus.AVAILABLE
            and self.has_capacity
        )


class AgentLocation(Base):
    """Append-only history of agent location pings."""

    __tablename__ = "agent_locations"
    __table_args__ = (Index("ix_agent_locations_agent_time", "agent_id", "recorded_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_agents.id", ondelete="CASCADE"), nullable=False
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    agent: Mapped["DeliveryAgent"] = relationship(back_populates="locations")
