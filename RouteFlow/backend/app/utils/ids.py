"""Identifier helpers."""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import settings


def generate_order_number(order_id: int, created: datetime | None = None) -> str:
    """Build a human-friendly, unique order number: ``RF-YYYYMMDD-000123``.

    The numeric suffix is derived from the database primary key, guaranteeing
    uniqueness without a separate sequence or race conditions.
    """
    created = created or datetime.now(timezone.utc)
    return f"{settings.ORDER_ID_PREFIX}-{created:%Y%m%d}-{order_id:06d}"
