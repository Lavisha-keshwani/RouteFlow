"""Rate card and COD surcharge management + rate lookup."""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.enums import OrderType, ZoneType
from app.domain.errors import (
    NotFoundError,
    OverlappingWeightRangeError,
    RateCardNotFoundError,
)
from app.domain.pricing import weight_ranges_overlap
from app.models.rate import CodSurcharge, RateCard
from app.schemas.rate import (
    CodSurchargeUpsert,
    RateCardCreate,
    RateCardUpdate,
)


class RateService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Rate cards ---
    def list_rate_cards(
        self,
        order_type: Optional[OrderType] = None,
        zone_type: Optional[ZoneType] = None,
    ) -> List[RateCard]:
        query = self.db.query(RateCard)
        if order_type is not None:
            query = query.filter(RateCard.order_type == order_type)
        if zone_type is not None:
            query = query.filter(RateCard.zone_type == zone_type)
        return query.order_by(
            RateCard.order_type, RateCard.zone_type, RateCard.min_weight_kg
        ).all()

    def create_rate_card(self, data: RateCardCreate) -> RateCard:
        self._assert_no_overlap(
            data.order_type, data.zone_type, data.min_weight_kg, data.max_weight_kg
        )
        card = RateCard(
            order_type=data.order_type,
            zone_type=data.zone_type,
            min_weight_kg=data.min_weight_kg,
            max_weight_kg=data.max_weight_kg,
            base_charge=data.base_charge,
            currency=data.currency,
            is_active=data.is_active,
        )
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)
        return card

    def update_rate_card(self, card_id: int, data: RateCardUpdate) -> RateCard:
        card = self.db.get(RateCard, card_id)
        if card is None:
            raise RateCardNotFoundError(f"Rate card {card_id} not found.")
        payload = data.model_dump(exclude_unset=True)
        new_min = payload.get("min_weight_kg", card.min_weight_kg)
        new_max = payload.get("max_weight_kg", card.max_weight_kg)
        if new_max <= new_min:
            raise OverlappingWeightRangeError(
                "max_weight_kg must be greater than min_weight_kg."
            )
        self._assert_no_overlap(
            card.order_type, card.zone_type, new_min, new_max, exclude_id=card.id
        )
        for field, value in payload.items():
            setattr(card, field, value)
        self.db.commit()
        self.db.refresh(card)
        return card

    def delete_rate_card(self, card_id: int) -> None:
        card = self.db.get(RateCard, card_id)
        if card is None:
            raise RateCardNotFoundError(f"Rate card {card_id} not found.")
        self.db.delete(card)
        self.db.commit()

    def _assert_no_overlap(
        self,
        order_type: OrderType,
        zone_type: ZoneType,
        min_weight: Decimal,
        max_weight: Decimal,
        exclude_id: Optional[int] = None,
    ) -> None:
        existing = (
            self.db.query(RateCard)
            .filter(
                RateCard.order_type == order_type,
                RateCard.zone_type == zone_type,
                RateCard.is_active.is_(True),
            )
            .all()
        )
        for card in existing:
            if exclude_id is not None and card.id == exclude_id:
                continue
            if weight_ranges_overlap(
                min_weight, max_weight, card.min_weight_kg, card.max_weight_kg
            ):
                raise OverlappingWeightRangeError(
                    f"Weight range ({min_weight}, {max_weight}] overlaps existing "
                    f"bracket ({card.min_weight_kg}, {card.max_weight_kg}] for "
                    f"{order_type.value}/{zone_type.value}.",
                    details={"conflicting_rate_card_id": card.id},
                )

    def lookup_rate_card(
        self,
        order_type: OrderType,
        zone_type: ZoneType,
        chargeable_weight: Decimal,
    ) -> RateCard:
        """Select the active rate card whose half-open ``(min, max]`` bracket
        contains the chargeable weight."""
        card = (
            self.db.query(RateCard)
            .filter(
                RateCard.order_type == order_type,
                RateCard.zone_type == zone_type,
                RateCard.is_active.is_(True),
                RateCard.min_weight_kg < chargeable_weight,
                RateCard.max_weight_kg >= chargeable_weight,
            )
            .order_by(RateCard.min_weight_kg)
            .first()
        )
        if card is None:
            raise RateCardNotFoundError(
                f"No rate card configured for {order_type.value}/{zone_type.value} "
                f"at {chargeable_weight} kg.",
                details={
                    "order_type": order_type.value,
                    "zone_type": zone_type.value,
                    "chargeable_weight": str(chargeable_weight),
                },
            )
        return card

    # --- COD surcharges ---
    def list_cod_surcharges(self) -> List[CodSurcharge]:
        return self.db.query(CodSurcharge).order_by(CodSurcharge.order_type).all()

    def upsert_cod_surcharge(self, data: CodSurchargeUpsert) -> CodSurcharge:
        row = (
            self.db.query(CodSurcharge)
            .filter(CodSurcharge.order_type == data.order_type)
            .first()
        )
        if row is None:
            row = CodSurcharge(order_type=data.order_type)
            self.db.add(row)
        row.amount = data.amount
        row.currency = data.currency
        row.is_active = data.is_active
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_cod_surcharge_amount(self, order_type: OrderType) -> Decimal:
        row = (
            self.db.query(CodSurcharge)
            .filter(
                CodSurcharge.order_type == order_type,
                CodSurcharge.is_active.is_(True),
            )
            .first()
        )
        if row is None:
            raise NotFoundError(
                f"No COD surcharge configured for {order_type.value}.",
                code="COD_SURCHARGE_NOT_FOUND",
            )
        return row.amount
