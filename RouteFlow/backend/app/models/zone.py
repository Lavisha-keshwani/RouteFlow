"""Zone and Area ORM models (admin-managed Area → Zone mapping)."""
from __future__ import annotations

from typing import List

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Zone(Base, TimestampMixin):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    areas: Mapped[List["Area"]] = relationship(
        back_populates="zone", cascade="all, delete-orphan"
    )


class Area(Base, TimestampMixin):
    __tablename__ = "areas"
    __table_args__ = (
        UniqueConstraint("normalized_name", name="uq_area_normalized_name"),
        Index("ix_areas_zone_id", "zone_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    zone_id: Mapped[int] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    zone: Mapped["Zone"] = relationship(back_populates="areas")
