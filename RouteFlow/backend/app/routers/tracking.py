"""Tracking routes: immutable timeline for an order (owner/admin scoped)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.order import DeliveryAttemptOut, OrderDetail, StatusHistoryOut
from app.services.order_service import OrderService

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get(
    "/{order_id}",
    response_model=OrderDetail,
    summary="Full order detail including the immutable tracking timeline",
)
def track_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderDetail:
    service = OrderService(db)
    return OrderDetail.model_validate(service.get_detail_for_actor(order_id, user))


@router.get(
    "/{order_id}/timeline",
    response_model=List[StatusHistoryOut],
    summary="Ordered, append-only status history for an order",
)
def order_timeline(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[StatusHistoryOut]:
    service = OrderService(db)
    order = service.get_detail_for_actor(order_id, user)
    return [StatusHistoryOut.model_validate(h) for h in order.status_history]


@router.get(
    "/{order_id}/attempts",
    response_model=List[DeliveryAttemptOut],
    summary="All delivery attempts for an order (history preserved)",
)
def order_attempts(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[DeliveryAttemptOut]:
    service = OrderService(db)
    order = service.get_detail_for_actor(order_id, user)
    return [DeliveryAttemptOut.model_validate(a) for a in order.attempts]
