"""Order, package, quote and tracking schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    DeliveryAttemptStatus,
    FailureReason,
    OrderStatus,
    OrderType,
    PaymentType,
    UserRole,
    ZoneType,
)


class PackageInput(BaseModel):
    length_cm: Decimal = Field(gt=0, le=1000)
    width_cm: Decimal = Field(gt=0, le=1000)
    height_cm: Decimal = Field(gt=0, le=1000)
    actual_weight_kg: Decimal = Field(gt=0, le=1000)


class QuoteRequest(PackageInput):
    pickup_address: str = Field(min_length=3, max_length=500)
    drop_address: str = Field(min_length=3, max_length=500)
    order_type: OrderType
    payment_type: PaymentType


class QuoteResponse(BaseModel):
    actual_weight: Decimal
    volumetric_weight: Decimal
    chargeable_weight: Decimal
    pickup_zone: str
    drop_zone: str
    pickup_zone_id: int
    drop_zone_id: int
    zone_type: ZoneType
    order_type: OrderType
    payment_type: PaymentType
    base_charge: Decimal
    cod_surcharge: Decimal
    total_charge: Decimal
    currency: str = "INR"
    rate_card_id: Optional[int] = None


class OrderCreate(QuoteRequest):
    # Admins may create on behalf of a customer; customers omit this.
    customer_id: Optional[int] = None


class PackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    length_cm: Decimal
    width_cm: Decimal
    height_cm: Decimal
    actual_weight_kg: Decimal
    volumetric_weight_kg: Decimal
    chargeable_weight_kg: Decimal


class StatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    old_status: Optional[OrderStatus] = None
    new_status: OrderStatus
    actor_role: Optional[UserRole] = None
    reason: Optional[str] = None
    created_at: datetime


class DeliveryAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attempt_number: int
    agent_id: Optional[int] = None
    status: DeliveryAttemptStatus
    scheduled_date: Optional[date] = None
    time_window: Optional[str] = None
    failure_reason: Optional[FailureReason] = None
    notes: Optional[str] = None
    assignment_score: Optional[float] = None


class AgentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: Optional[str] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    customer_id: int
    status: OrderStatus
    order_type: OrderType
    payment_type: PaymentType
    zone_type: ZoneType
    pickup_address: str
    drop_address: str
    pickup_zone_id: int
    drop_zone_id: int
    assigned_agent_id: Optional[int] = None
    chargeable_weight_kg: Decimal
    base_charge: Decimal
    cod_surcharge: Decimal
    total_charge: Decimal
    currency: str
    confirmed_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime


class OrderDetail(OrderOut):
    package: Optional[PackageOut] = None
    status_history: List[StatusHistoryOut] = []
    attempts: List[DeliveryAttemptOut] = []


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    reason: Optional[str] = Field(default=None, max_length=500)


class OrderFailInput(BaseModel):
    failure_reason: FailureReason
    notes: Optional[str] = Field(default=None, max_length=500)


class RescheduleInput(BaseModel):
    new_date: date
    time_window: Optional[str] = Field(default=None, max_length=50)
    reason: Optional[str] = Field(default=None, max_length=500)


class AssignAgentInput(BaseModel):
    agent_id: int
    reason: Optional[str] = Field(default=None, max_length=500)
