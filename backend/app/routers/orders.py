"""Order routes: quote, create, list, detail, confirm, reschedule."""
from __future__ import annotations

import math
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_notification_service
from app.domain.enums import OrderStatus, OrderType, PaymentType
from app.models.user import User
from app.notifications.service import NotificationService
from app.schemas.common import Page
from app.schemas.order import (
    OrderCreate,
    OrderDetail,
    OrderFailInput,
    OrderOut,
    OrderStatusUpdate,
    QuoteRequest,
    QuoteResponse,
    RescheduleInput,
)
from app.services.order_service import OrderService
from app.services.pricing_service import PricingService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/quote", response_model=QuoteResponse, summary="Get a transparent price quote")
def quote(
    data: QuoteRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> QuoteResponse:
    """Detect zones, compute chargeable weight and return a full price breakdown.

    No order is created. Available to customers and admins.
    """
    return PricingService(db).quote(data)


@router.post(
    "",
    response_model=OrderDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order (customer, or admin on behalf of a customer)",
)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    notifier: NotificationService = Depends(get_notification_service),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> OrderDetail:
    """Create an order with an immutable pricing snapshot.

    Supply an ``Idempotency-Key`` header to safely retry without creating
    duplicate orders.
    """
    service = OrderService(db, notifier)
    order = service.create_order(data, user, idempotency_key=idempotency_key)
    return OrderDetail.model_validate(service.get_detail_for_actor(order.id, user))


@router.get("", response_model=Page[OrderOut], summary="List orders (role-scoped)")
def list_orders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status_filter: Optional[OrderStatus] = Query(default=None, alias="status"),
    zone_id: Optional[int] = None,
    order_type: Optional[OrderType] = None,
    payment_type: Optional[PaymentType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[OrderOut]:
    service = OrderService(db)
    items, total = service.list_orders(
        user,
        status=status_filter,
        zone_id=zone_id,
        order_type=order_type,
        payment_type=payment_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return Page[OrderOut](
        items=[OrderOut.model_validate(o) for o in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{order_id}", response_model=OrderDetail, summary="Get order detail with timeline")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderDetail:
    service = OrderService(db)
    return OrderDetail.model_validate(service.get_detail_for_actor(order_id, user))


@router.post(
    "/{order_id}/confirm", response_model=OrderDetail, summary="Confirm a pending order"
)
def confirm_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    notifier: NotificationService = Depends(get_notification_service),
) -> OrderDetail:
    service = OrderService(db, notifier)
    service.confirm_order(order_id, user)
    return OrderDetail.model_validate(service.get_detail_for_actor(order_id, user))


@router.post(
    "/{order_id}/reschedule",
    response_model=OrderDetail,
    summary="Reschedule a failed delivery (creates a new attempt)",
)
def reschedule_order(
    order_id: int,
    data: RescheduleInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    notifier: NotificationService = Depends(get_notification_service),
) -> OrderDetail:
    service = OrderService(db, notifier)
    service.reschedule(
        order_id,
        user,
        new_date=data.new_date,
        time_window=data.time_window,
        reason=data.reason,
    )
    return OrderDetail.model_validate(service.get_detail_for_actor(order_id, user))


@router.patch(
    "/{order_id}/status",
    response_model=OrderDetail,
    summary="Advance order status (assigned agent or admin)",
)
def update_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    notifier: NotificationService = Depends(get_notification_service),
) -> OrderDetail:
    """Move an order to the next valid status. The state machine rejects illegal
    transitions; agents may only set delivery statuses on their own orders."""
    service = OrderService(db, notifier)
    service.update_status(order_id, data.status, user, reason=data.reason)
    return OrderDetail.model_validate(service.get_detail_for_actor(order_id, user))


@router.post(
    "/{order_id}/fail",
    response_model=OrderDetail,
    summary="Mark an out-for-delivery order as failed (assigned agent or admin)",
)
def fail_order(
    order_id: int,
    data: OrderFailInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    notifier: NotificationService = Depends(get_notification_service),
) -> OrderDetail:
    service = OrderService(db, notifier)
    service.fail_delivery(order_id, data.failure_reason, user, notes=data.notes)
    return OrderDetail.model_validate(service.get_detail_for_actor(order_id, user))
