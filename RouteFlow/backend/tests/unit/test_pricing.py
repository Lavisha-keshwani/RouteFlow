"""Unit tests for the rate calculation engine (pure domain logic)."""
from decimal import Decimal

import pytest

from app.domain.enums import OrderType, PaymentType, ZoneType
from app.domain.errors import InvalidDimensionsError, InvalidWeightError
from app.domain.pricing import (
    build_price_breakdown,
    calculate_chargeable_weight,
    calculate_volumetric_weight,
    determine_zone_type,
    weight_ranges_overlap,
)


class TestVolumetricWeight:
    def test_spec_example(self):
        # 50 x 40 x 30 / 5000 = 12 kg
        assert calculate_volumetric_weight(50, 40, 30) == Decimal("12.000")

    def test_custom_divisor(self):
        assert calculate_volumetric_weight(10, 10, 10, divisor=1000) == Decimal("1.000")

    @pytest.mark.parametrize("l,w,h", [(0, 10, 10), (10, -1, 10), (10, 10, 0)])
    def test_non_positive_dimensions_raise(self, l, w, h):
        with pytest.raises(InvalidDimensionsError):
            calculate_volumetric_weight(l, w, h)


class TestChargeableWeight:
    def test_actual_greater_than_volumetric(self):
        assert calculate_chargeable_weight(Decimal("15"), Decimal("12")) == Decimal("15.000")

    def test_volumetric_greater_than_actual(self):
        # spec example: actual 8, volumetric 12 -> 12
        assert calculate_chargeable_weight(Decimal("8"), Decimal("12")) == Decimal("12.000")

    def test_equal_weights(self):
        assert calculate_chargeable_weight(Decimal("10"), Decimal("10")) == Decimal("10.000")

    def test_zero_actual_raises(self):
        with pytest.raises(InvalidWeightError):
            calculate_chargeable_weight(Decimal("0"), Decimal("5"))


class TestZoneType:
    def test_same_zone_is_intra(self):
        assert determine_zone_type(1, 1) == ZoneType.INTRA_ZONE

    def test_different_zone_is_inter(self):
        assert determine_zone_type(1, 2) == ZoneType.INTER_ZONE


class TestPriceBreakdown:
    def test_prepaid_has_no_cod_surcharge(self):
        b = build_price_breakdown(
            actual_weight=Decimal("8"),
            volumetric_weight=Decimal("12"),
            order_type=OrderType.B2C,
            payment_type=PaymentType.PREPAID,
            zone_type=ZoneType.INTER_ZONE,
            base_charge=Decimal("130"),
            configured_cod_surcharge=Decimal("30"),
            rate_card_id=1,
        )
        assert b.cod_surcharge == Decimal("0.00")
        assert b.total_charge == Decimal("130.00")
        assert b.chargeable_weight == Decimal("12.000")

    def test_cod_applies_surcharge(self):
        b = build_price_breakdown(
            actual_weight=Decimal("8"),
            volumetric_weight=Decimal("12"),
            order_type=OrderType.B2C,
            payment_type=PaymentType.COD,
            zone_type=ZoneType.INTER_ZONE,
            base_charge=Decimal("130"),
            configured_cod_surcharge=Decimal("30"),
            rate_card_id=1,
        )
        # spec example: 130 base + 30 COD = 160
        assert b.cod_surcharge == Decimal("30.00")
        assert b.total_charge == Decimal("160.00")


class TestWeightRangeOverlap:
    def test_overlapping_ranges(self):
        # 0-5 and 4-10 overlap
        assert weight_ranges_overlap(
            Decimal("0"), Decimal("5"), Decimal("4"), Decimal("10")
        )

    def test_adjacent_ranges_do_not_overlap(self):
        # (0,5] and (5,10] are adjacent, not overlapping
        assert not weight_ranges_overlap(
            Decimal("0"), Decimal("5"), Decimal("5"), Decimal("10")
        )
