"""Notification and analytics schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from app.domain.enums import (
    NotificationChannel,
    NotificationEvent,
    NotificationStatus,
)


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: Optional[int] = None
    recipient: str
    channel: NotificationChannel
    event_type: NotificationEvent
    subject: Optional[str] = None
    message: str
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    created_at: datetime


class StatusCount(BaseModel):
    status: str
    count: int


class ZoneCount(BaseModel):
    zone: str
    count: int


class DailyVolume(BaseModel):
    date: str
    count: int


class AnalyticsSummary(BaseModel):
    total_orders: int
    active_orders: int
    delivered: int
    failed: int
    pending: int
    revenue: Decimal
    cod_orders: int
    cod_percentage: float
    delivery_success_rate: float
    failed_delivery_rate: float
    average_order_value: Decimal
    agent_utilization: float
    orders_by_status: List[StatusCount]
    orders_by_zone: List[ZoneCount]
    daily_volume: List[DailyVolume]
    failure_rate_by_zone: Dict[str, float]
