"""Notification routes (role-scoped)."""
from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domain.enums import NotificationStatus, UserRole
from app.models.notification import Notification
from app.models.order import Order
from app.models.user import Customer, User
from app.schemas.common import Page
from app.schemas.notification import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationOut], summary="List notifications")
def list_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status_filter: Optional[NotificationStatus] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[NotificationOut]:
    query = db.query(Notification)

    if user.role == UserRole.CUSTOMER:
        customer = db.query(Customer).filter(Customer.user_id == user.id).first()
        customer_id = customer.id if customer else -1
        query = query.join(Order, Notification.order_id == Order.id).filter(
            Order.customer_id == customer_id
        )
    elif user.role != UserRole.ADMIN:
        # Agents do not have a notification inbox in this product.
        query = query.filter(Notification.id.is_(None))

    if status_filter is not None:
        query = query.filter(Notification.status == status_filter)

    total = query.count()
    items = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Page[NotificationOut](
        items=[NotificationOut.model_validate(n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )
