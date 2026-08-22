"""Rate calculation engine (pure domain logic).

This module contains **no** hardcoded business rates. It computes volumetric and
chargeable weight and assembles a transparent price breakdown from values that
the caller supplies after looking them up in admin-configured rate cards.

Monetary amounts are always :class:`~decimal.Decimal` — never floats.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Optional

from app.domain.enums import OrderType, PaymentType, ZoneType
from app.domain.errors import InvalidDimensionsError, InvalidWeightError

MONEY_QUANTUM = Decimal("0.01")
WEIGHT_QUANTUM = Decimal("0.001")
CURRENCY = "INR"


def quantize_money(amount: Decimal) -> Decimal:
    """Round a monetary value to 2 decimal places (half-up)."""
    return amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def quantize_weight(weight: Decimal) -> Decimal:
    """Round a weight (kg) to 3 decimal places (half-up)."""
    return weight.quantize(WEIGHT_QUANTUM, rounding=ROUND_HALF_UP)


def _to_decimal(value: object, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:  # pragma: no cover
        raise InvalidDimensionsError(f"{field} is not a valid number.") from exc


def calculate_volumetric_weight(
    length_cm: object,
    width_cm: object,
    height_cm: object,
    divisor: int = 5000,
) -> Decimal:
    """Volumetric weight = (L × B × H) / divisor.

    Dimensions are in centimetres; the result is in kilograms. Raises
    :class:`InvalidDimensionsError` for non-positive dimensions.
    """
    length = _to_decimal(length_cm, "length")
    width = _to_decimal(width_cm, "width")
    height = _to_decimal(height_cm, "height")

    if length <= 0 or width <= 0 or height <= 0:
        raise InvalidDimensionsError("Dimensions must be positive numbers (cm).")
    if divisor <= 0:
        raise InvalidDimensionsError("Volumetric divisor must be positive.")

    volumetric = (length * width * height) / Decimal(divisor)
    return quantize_weight(volumetric)


def calculate_chargeable_weight(actual_weight: object, volumetric_weight: object) -> Decimal:
    """Chargeable weight = max(actual, volumetric). Raises on non-positive actual."""
    actual = _to_decimal(actual_weight, "actual_weight")
    volumetric = _to_decimal(volumetric_weight, "volumetric_weight")

    if actual <= 0:
        raise InvalidWeightError("Actual weight must be a positive number (kg).")

    return quantize_weight(max(actual, volumetric))


def determine_zone_type(pickup_zone_id: int, drop_zone_id: int) -> ZoneType:
    """Intra-zone when pickup and drop resolve to the same zone, else inter-zone."""
    return (
        ZoneType.INTRA_ZONE
        if pickup_zone_id == drop_zone_id
        else ZoneType.INTER_ZONE
    )


@dataclass(frozen=True)
class PriceBreakdown:
    """Immutable, fully explainable pricing result."""

    actual_weight: Decimal
    volumetric_weight: Decimal
    chargeable_weight: Decimal
    order_type: OrderType
    payment_type: PaymentType
    zone_type: ZoneType
    base_charge: Decimal
    cod_surcharge: Decimal
    total_charge: Decimal
    rate_card_id: Optional[int] = None
    currency: str = CURRENCY


def build_price_breakdown(
    *,
    actual_weight: Decimal,
    volumetric_weight: Decimal,
    order_type: OrderType,
    payment_type: PaymentType,
    zone_type: ZoneType,
    base_charge: Decimal,
    configured_cod_surcharge: Decimal,
    rate_card_id: Optional[int] = None,
) -> PriceBreakdown:
    """Assemble the final price breakdown.

    The COD surcharge is applied only for COD payments; prepaid orders always
    carry a zero surcharge regardless of what is configured.
    """
    chargeable_weight = calculate_chargeable_weight(actual_weight, volumetric_weight)

    cod_surcharge = (
        quantize_money(configured_cod_surcharge)
        if payment_type == PaymentType.COD
        else Decimal("0.00")
    )
    base = quantize_money(base_charge)
    total = quantize_money(base + cod_surcharge)

    return PriceBreakdown(
        actual_weight=quantize_weight(Decimal(str(actual_weight))),
        volumetric_weight=quantize_weight(Decimal(str(volumetric_weight))),
        chargeable_weight=chargeable_weight,
        order_type=order_type,
        payment_type=payment_type,
        zone_type=zone_type,
        base_charge=base,
        cod_surcharge=cod_surcharge,
        total_charge=total,
        rate_card_id=rate_card_id,
        currency=CURRENCY,
    )


def weight_ranges_overlap(
    a_min: Decimal, a_max: Decimal, b_min: Decimal, b_max: Decimal
) -> bool:
    """Return ``True`` if two half-open weight ranges ``(min, max]`` overlap.

    Used by admin rate-card validation to reject configurations such as
    ``0–5`` and ``4–10``.
    """
    return a_min < b_max and b_min < a_max
