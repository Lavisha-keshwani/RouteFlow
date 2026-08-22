"""Analytics service: operational metrics derived from real order data."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from sqlalchemy import case, func

from sqlalchemy.orm import Session

from app.domain.enums import (
    DeliveryAttemptStatus,
    OrderStatus,
    PaymentType,
)
from app.models.order import DeliveryAttempt, Order
from app.models.user import DeliveryAgent
from app.models.zone import Zone
from app.schemas.notification import (
    AnalyticsSummary,
    DailyVolume,
    StatusCount,
    ZoneCount,
)

_ACTIVE_STATES = (
    OrderStatus.ASSIGNED,
    OrderStatus.PICKED_UP,
    OrderStatus.IN_TRANSIT,
    OrderStatus.OUT_FOR_DELIVERY,
)


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self) -> AnalyticsSummary:
        db = self.db
        total_orders = db.query(func.count(Order.id)).scalar() or 0

        def count_status(status: OrderStatus) -> int:
            return db.query(func.count(Order.id)).filter(Order.status == status).scalar() or 0

        delivered = count_status(OrderStatus.DELIVERED)
        failed = count_status(OrderStatus.FAILED)
        pending = count_status(OrderStatus.PENDING_CONFIRMATION)
        active = (
            db.query(func.count(Order.id)).filter(Order.status.in_(_ACTIVE_STATES)).scalar()
            or 0
        )

        revenue = (
            db.query(func.coalesce(func.sum(Order.total_charge), 0))
            .filter(Order.status == OrderStatus.DELIVERED)
            .scalar()
            or Decimal("0")
        )
        cod_orders = (
            db.query(func.count(Order.id))
            .filter(Order.payment_type == PaymentType.COD)
            .scalar()
            or 0
        )
        avg_value = (
            db.query(func.coalesce(func.avg(Order.total_charge), 0)).scalar() or Decimal("0")
        )

        # Attempt-based delivery outcome rates.
        total_finished_attempts = (
            db.query(func.count(DeliveryAttempt.id))
            .filter(
                DeliveryAttempt.status.in_(
                    (DeliveryAttemptStatus.DELIVERED, DeliveryAttemptStatus.FAILED)
                )
            )
            .scalar()
            or 0
        )
        delivered_attempts = (
            db.query(func.count(DeliveryAttempt.id))
            .filter(DeliveryAttempt.status == DeliveryAttemptStatus.DELIVERED)
            .scalar()
            or 0
        )
        failed_attempts = total_finished_attempts - delivered_attempts

        success_rate = (
            round(delivered_attempts / total_finished_attempts * 100, 2)
            if total_finished_attempts
            else 0.0
        )
        failure_rate = (
            round(failed_attempts / total_finished_attempts * 100, 2)
            if total_finished_attempts
            else 0.0
        )
        cod_percentage = round(cod_orders / total_orders * 100, 2) if total_orders else 0.0

        # Agent utilization = engaged capacity / total capacity of active agents.
        capacity = (
            db.query(
                func.coalesce(func.sum(DeliveryAgent.active_orders), 0),
                func.coalesce(func.sum(DeliveryAgent.max_active_orders), 0),
            )
            .filter(DeliveryAgent.is_active.is_(True))
            .one()
        )
        engaged, total_capacity = capacity
        utilization = round((engaged or 0) / total_capacity * 100, 2) if total_capacity else 0.0

        return AnalyticsSummary(
            total_orders=total_orders,
            active_orders=active,
            delivered=delivered,
            failed=failed,
            pending=pending,
            revenue=Decimal(revenue),
            cod_orders=cod_orders,
            cod_percentage=cod_percentage,
            delivery_success_rate=success_rate,
            failed_delivery_rate=failure_rate,
            average_order_value=Decimal(avg_value).quantize(Decimal("0.01")),
            agent_utilization=utilization,
            orders_by_status=self._orders_by_status(),
            orders_by_zone=self._orders_by_zone(),
            daily_volume=self._daily_volume(),
            failure_rate_by_zone=self._failure_rate_by_zone(),
        )

    def _orders_by_status(self) -> List[StatusCount]:
        rows = (
            self.db.query(Order.status, func.count(Order.id))
            .group_by(Order.status)
            .all()
        )
        return [StatusCount(status=s.value, count=c) for s, c in rows]

    def _orders_by_zone(self) -> List[ZoneCount]:
        rows = (
            self.db.query(Zone.code, func.count(Order.id))
            .join(Order, Order.pickup_zone_id == Zone.id)
            .group_by(Zone.code)
            .all()
        )
        return [ZoneCount(zone=code, count=count) for code, count in rows]

    def _daily_volume(self) -> List[DailyVolume]:
        rows = (
            self.db.query(
                func.date(Order.created_at).label("day"), func.count(Order.id)
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
            .all()
        )
        return [DailyVolume(date=str(day), count=count) for day, count in rows[-14:]]

    def _failure_rate_by_zone(self) -> Dict[str, float]:
        failed_case = case(
            (DeliveryAttempt.status == DeliveryAttemptStatus.FAILED, 1), else_=0
        )
        rows = (
            self.db.query(
                Zone.code,
                func.count(DeliveryAttempt.id),
                func.coalesce(func.sum(failed_case), 0),
            )
            .join(Order, Order.pickup_zone_id == Zone.id)
            .join(DeliveryAttempt, DeliveryAttempt.order_id == Order.id)
            .filter(
                DeliveryAttempt.status.in_(
                    (DeliveryAttemptStatus.DELIVERED, DeliveryAttemptStatus.FAILED)
                )
            )
            .group_by(Zone.code)
            .all()
        )
        result: Dict[str, float] = {}
        for code, total, failed in rows:
            total = total or 0
            failed = failed or 0
            result[code] = round(failed / total * 100, 2) if total else 0.0
        return result
