"""Rate card and COD surcharge schemas."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import OrderType, ZoneType


class RateCardCreate(BaseModel):
    order_type: OrderType
    zone_type: ZoneType
    min_weight_kg: Decimal = Field(ge=0)
    max_weight_kg: Decimal = Field(gt=0)
    base_charge: Decimal = Field(ge=0)
    currency: str = "INR"
    is_active: bool = True

    @model_validator(mode="after")
    def _check_range(self) -> "RateCardCreate":
        if self.max_weight_kg <= self.min_weight_kg:
            raise ValueError("max_weight_kg must be greater than min_weight_kg")
        return self


class RateCardUpdate(BaseModel):
    min_weight_kg: Optional[Decimal] = Field(default=None, ge=0)
    max_weight_kg: Optional[Decimal] = Field(default=None, gt=0)
    base_charge: Optional[Decimal] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class RateCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_type: OrderType
    zone_type: ZoneType
    min_weight_kg: Decimal
    max_weight_kg: Decimal
    base_charge: Decimal
    currency: str
    is_active: bool


class CodSurchargeUpsert(BaseModel):
    order_type: OrderType
    amount: Decimal = Field(ge=0)
    currency: str = "INR"
    is_active: bool = True


class CodSurchargeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_type: OrderType
    amount: Decimal
    currency: str
    is_active: bool
