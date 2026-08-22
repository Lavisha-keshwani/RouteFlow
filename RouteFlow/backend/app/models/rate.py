"""Rate card and COD surcharge ORM models (admin-configurable pricing)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SQLEnum,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domain.enums import OrderType, ZoneType
from app.models.mixins import TimestampMixin


class RateCard(Base, TimestampMixin):
    """A single weight-bracket rate for an (order_type, zone_type) combination.

    Brackets are half-open ``(min_weight_kg, max_weight_kg]``; a package on a
    boundary is billed at the lower bracket. Overlapping brackets are rejected by
    the admin service.
    """

    __tablename__ = "rate_cards"
    __table_args__ = (
        CheckConstraint("min_weight_kg >= 0", name="ck_rate_min_nonneg"),
        CheckConstraint("max_weight_kg > min_weight_kg", name="ck_rate_range_valid"),
        CheckConstraint("base_charge >= 0", name="ck_rate_charge_nonneg"),
        Index("ix_rate_lookup", "order_type", "zone_type", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_type: Mapped[OrderType] = mapped_column(
        SQLEnum(OrderType, native_enum=False, length=10), nullable=False
    )
    zone_type: Mapped[ZoneType] = mapped_column(
        SQLEnum(ZoneType, native_enum=False, length=15), nullable=False
    )
    min_weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    max_weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    base_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CodSurcharge(Base, TimestampMixin):
    """COD surcharge configured per order type."""

    __tablename__ = "cod_surcharges"
    __table_args__ = (
        UniqueConstraint("order_type", name="uq_cod_order_type"),
        CheckConstraint("amount >= 0", name="ck_cod_amount_nonneg"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_type: Mapped[OrderType] = mapped_column(
        SQLEnum(OrderType, native_enum=False, length=10), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
