"""Pricing service: turns a quote request into a full, explainable breakdown.

Orchestrates zone detection, weight calculation, rate-card lookup and COD
surcharge — all sourced from admin-configured data, never hardcoded.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.enums import PaymentType
from app.domain.pricing import (
    PriceBreakdown,
    build_price_breakdown,
    calculate_chargeable_weight,
    calculate_volumetric_weight,
    determine_zone_type,
)
from app.models.zone import Area, Zone
from app.schemas.order import QuoteRequest, QuoteResponse
from app.services.rate_service import RateService
from app.services.zone_service import ZoneService


class PricingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.zones = ZoneService(db)
        self.rates = RateService(db)

    def compute(self, request: QuoteRequest) -> tuple[PriceBreakdown, Zone, Zone, Area, Area]:
        """Compute a price breakdown and the resolved zones/areas.

        Returned tuple: ``(breakdown, pickup_zone, drop_zone, pickup_area,
        drop_area)`` so the order service can persist zone/area references.
        """
        pickup_area, pickup_zone = self.zones.detect_zone(request.pickup_address)
        drop_area, drop_zone = self.zones.detect_zone(request.drop_address)

        volumetric = calculate_volumetric_weight(
            request.length_cm,
            request.width_cm,
            request.height_cm,
            divisor=settings.VOLUMETRIC_DIVISOR,
        )
        chargeable = calculate_chargeable_weight(request.actual_weight_kg, volumetric)
        zone_type = determine_zone_type(pickup_zone.id, drop_zone.id)

        rate_card = self.rates.lookup_rate_card(
            request.order_type, zone_type, chargeable
        )

        cod_amount: Decimal = Decimal("0.00")
        if request.payment_type == PaymentType.COD:
            cod_amount = self.rates.get_cod_surcharge_amount(request.order_type)

        breakdown = build_price_breakdown(
            actual_weight=request.actual_weight_kg,
            volumetric_weight=volumetric,
            order_type=request.order_type,
            payment_type=request.payment_type,
            zone_type=zone_type,
            base_charge=rate_card.base_charge,
            configured_cod_surcharge=cod_amount,
            rate_card_id=rate_card.id,
        )
        return breakdown, pickup_zone, drop_zone, pickup_area, drop_area

    def quote(self, request: QuoteRequest) -> QuoteResponse:
        breakdown, pickup_zone, drop_zone, _, _ = self.compute(request)
        return QuoteResponse(
            actual_weight=breakdown.actual_weight,
            volumetric_weight=breakdown.volumetric_weight,
            chargeable_weight=breakdown.chargeable_weight,
            pickup_zone=pickup_zone.code,
            drop_zone=drop_zone.code,
            pickup_zone_id=pickup_zone.id,
            drop_zone_id=drop_zone.id,
            zone_type=breakdown.zone_type,
            order_type=breakdown.order_type,
            payment_type=breakdown.payment_type,
            base_charge=breakdown.base_charge,
            cod_surcharge=breakdown.cod_surcharge,
            total_charge=breakdown.total_charge,
            currency=breakdown.currency,
            rate_card_id=breakdown.rate_card_id,
        )
