"""Order repository: encapsulates filtered, paginated order queries.

Keeps complex query construction out of the service and ensures admin listings
are always server-side filtered and paginated (never load-all).
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import OrderStatus, OrderType, PaymentType
from app.models.order import Order


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, order_id: int) -> Optional[Order]:
        return self.db.get(Order, order_id)

    def get_detail(self, order_id: int) -> Optional[Order]:
        return (
            self.db.query(Order)
            .options(
                selectinload(Order.package),
                selectinload(Order.status_history),
                selectinload(Order.attempts),
            )
            .filter(Order.id == order_id)
            .first()
        )

    def get_by_number(self, order_number: str) -> Optional[Order]:
        return self.db.query(Order).filter(Order.order_number == order_number).first()

    def list(
        self,
        *,
        customer_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        status: Optional[OrderStatus] = None,
        zone_id: Optional[int] = None,
        order_type: Optional[OrderType] = None,
        payment_type: Optional[PaymentType] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Order], int]:
        query = self.db.query(Order)

        if customer_id is not None:
            query = query.filter(Order.customer_id == customer_id)
        if agent_id is not None:
            query = query.filter(Order.assigned_agent_id == agent_id)
        if status is not None:
            query = query.filter(Order.status == status)
        if zone_id is not None:
            query = query.filter(
                (Order.pickup_zone_id == zone_id) | (Order.drop_zone_id == zone_id)
            )
        if order_type is not None:
            query = query.filter(Order.order_type == order_type)
        if payment_type is not None:
            query = query.filter(Order.payment_type == payment_type)
        if date_from is not None:
            query = query.filter(
                Order.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
            )
        if date_to is not None:
            query = query.filter(
                Order.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc)
            )

        total = query.with_entities(func.count(Order.id)).scalar() or 0
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        items = (
            query.order_by(Order.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total
