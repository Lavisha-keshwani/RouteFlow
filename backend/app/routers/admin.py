"""Admin routes: zones, areas, rate cards, COD, agents, orders, assignment.

All routes require the ADMIN role (enforced by the router-level dependency).
"""
from __future__ import annotations

import math
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_notification_service, require_admin
from app.domain.enums import OrderStatus, OrderType, PaymentType, ZoneType
from app.models.user import DeliveryAgent, User
from app.notifications.service import NotificationService
from app.schemas.agent import (
    AgentCreate,
    AgentProfile,
    AgentUpdate,
    AssignmentResult,
    ScoredAgentOut,
)
from app.schemas.common import Message, Page
from app.schemas.order import AssignAgentInput, OrderDetail, OrderOut, OrderStatusUpdate
from app.schemas.rate import (
    CodSurchargeOut,
    CodSurchargeUpsert,
    RateCardCreate,
    RateCardOut,
    RateCardUpdate,
)
from app.schemas.zone import (
    AreaCreate,
    AreaOut,
    AreaUpdate,
    ZoneCreate,
    ZoneOut,
    ZoneUpdate,
    ZoneWithAreas,
)
from app.services.agent_service import AgentService
from app.services.order_service import OrderService
from app.services.rate_service import RateService
from app.services.zone_service import ZoneService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _agent_profile(db: Session, agent: DeliveryAgent) -> AgentProfile:
    user = db.get(User, agent.user_id)
    return AgentProfile(
        id=agent.id,
        status=agent.status,
        current_zone_id=agent.current_zone_id,
        current_latitude=agent.current_latitude,
        current_longitude=agent.current_longitude,
        last_location_update=agent.last_location_update,
        max_active_orders=agent.max_active_orders,
        active_orders=agent.active_orders,
        is_active=agent.is_active,
        full_name=user.full_name if user else "",
        email=user.email if user else "",
        phone=user.phone if user else None,
    )


def _scored_out(scored) -> ScoredAgentOut:
    return ScoredAgentOut(
        agent_id=scored.agent_id,
        name=scored.name,
        score=scored.score,
        distance_km=scored.distance_km,
        zone_score=scored.zone_score,
        workload_score=scored.workload_score,
        freshness_score=scored.freshness_score,
        distance_score=scored.distance_score,
        explanation=scored.explanation,
    )


# ----------------------------------------------------------------------- zones
@router.get("/zones", response_model=List[ZoneWithAreas], summary="List zones with areas")
def list_zones(db: Session = Depends(get_db)) -> List[ZoneWithAreas]:
    zones = ZoneService(db).list_zones()
    return [ZoneWithAreas.model_validate(z) for z in zones]


@router.post(
    "/zones",
    response_model=ZoneOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a zone",
)
def create_zone(data: ZoneCreate, db: Session = Depends(get_db)) -> ZoneOut:
    return ZoneOut.model_validate(ZoneService(db).create_zone(data))


@router.patch("/zones/{zone_id}", response_model=ZoneOut, summary="Update a zone")
def update_zone(zone_id: int, data: ZoneUpdate, db: Session = Depends(get_db)) -> ZoneOut:
    return ZoneOut.model_validate(ZoneService(db).update_zone(zone_id, data))


# ----------------------------------------------------------------------- areas
@router.get("/areas", response_model=List[AreaOut], summary="List areas")
def list_areas(
    zone_id: Optional[int] = None, db: Session = Depends(get_db)
) -> List[AreaOut]:
    return [AreaOut.model_validate(a) for a in ZoneService(db).list_areas(zone_id)]


@router.post(
    "/areas",
    response_model=AreaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an area and map it to a zone",
)
def create_area(data: AreaCreate, db: Session = Depends(get_db)) -> AreaOut:
    return AreaOut.model_validate(ZoneService(db).create_area(data))


@router.patch(
    "/areas/{area_id}",
    response_model=AreaOut,
    summary="Update an area (including moving it to another zone)",
)
def update_area(area_id: int, data: AreaUpdate, db: Session = Depends(get_db)) -> AreaOut:
    return AreaOut.model_validate(ZoneService(db).update_area(area_id, data))


# ------------------------------------------------------------------ rate cards
@router.get("/rates", response_model=List[RateCardOut], summary="List rate cards")
def list_rates(
    order_type: Optional[OrderType] = None,
    zone_type: Optional[ZoneType] = None,
    db: Session = Depends(get_db),
) -> List[RateCardOut]:
    cards = RateService(db).list_rate_cards(order_type, zone_type)
    return [RateCardOut.model_validate(c) for c in cards]


@router.post(
    "/rates",
    response_model=RateCardOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a rate card (rejects overlapping weight brackets)",
)
def create_rate(data: RateCardCreate, db: Session = Depends(get_db)) -> RateCardOut:
    return RateCardOut.model_validate(RateService(db).create_rate_card(data))


@router.patch("/rates/{card_id}", response_model=RateCardOut, summary="Update a rate card")
def update_rate(
    card_id: int, data: RateCardUpdate, db: Session = Depends(get_db)
) -> RateCardOut:
    return RateCardOut.model_validate(RateService(db).update_rate_card(card_id, data))


@router.delete("/rates/{card_id}", response_model=Message, summary="Delete a rate card")
def delete_rate(card_id: int, db: Session = Depends(get_db)) -> Message:
    RateService(db).delete_rate_card(card_id)
    return Message(message="Rate card deleted.")


# --------------------------------------------------------------- COD surcharges
@router.get(
    "/cod-surcharges", response_model=List[CodSurchargeOut], summary="List COD surcharges"
)
def list_cod(db: Session = Depends(get_db)) -> List[CodSurchargeOut]:
    return [CodSurchargeOut.model_validate(c) for c in RateService(db).list_cod_surcharges()]


@router.put(
    "/cod-surcharges",
    response_model=CodSurchargeOut,
    summary="Create or update a COD surcharge for an order type",
)
def upsert_cod(data: CodSurchargeUpsert, db: Session = Depends(get_db)) -> CodSurchargeOut:
    return CodSurchargeOut.model_validate(RateService(db).upsert_cod_surcharge(data))


# ---------------------------------------------------------------------- agents
@router.get("/agents", response_model=List[AgentProfile], summary="List delivery agents")
def list_agents(db: Session = Depends(get_db)) -> List[AgentProfile]:
    return [_agent_profile(db, a) for a in AgentService(db).list_agents()]


@router.post(
    "/agents",
    response_model=AgentProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Create a delivery agent",
)
def create_agent(data: AgentCreate, db: Session = Depends(get_db)) -> AgentProfile:
    return _agent_profile(db, AgentService(db).create_agent(data))


@router.patch("/agents/{agent_id}", response_model=AgentProfile, summary="Update an agent")
def update_agent(
    agent_id: int, data: AgentUpdate, db: Session = Depends(get_db)
) -> AgentProfile:
    return _agent_profile(db, AgentService(db).update_agent(agent_id, data))


# ---------------------------------------------------------------------- orders
@router.get("/orders", response_model=Page[OrderOut], summary="List all orders with filters")
def list_all_orders(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    status_filter: Optional[OrderStatus] = Query(default=None, alias="status"),
    zone_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    order_type: Optional[OrderType] = None,
    payment_type: Optional[PaymentType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[OrderOut]:
    items, total = OrderService(db).list_orders(
        admin,
        status=status_filter,
        zone_id=zone_id,
        agent_id=agent_id,
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


@router.post(
    "/orders/{order_id}/assign",
    response_model=AssignmentResult,
    summary="Manually assign a delivery agent to an order",
)
def assign_agent(
    order_id: int,
    data: AssignAgentInput,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    notifier: NotificationService = Depends(get_notification_service),
) -> AssignmentResult:
    service = OrderService(db, notifier)
    order, agent, _ = service.assign_agent_manual(order_id, data.agent_id, admin, data.reason)
    profile = _agent_profile(db, agent)
    return AssignmentResult(
        agent=profile,
        decision=ScoredAgentOut(
            agent_id=agent.id,
            name=profile.full_name,
            score=1.0,
            distance_km=None,
            zone_score=0.0,
            workload_score=0.0,
            freshness_score=0.0,
            distance_score=0.0,
            explanation="Manually assigned by admin.",
        ),
        candidates_considered=1,
        ranking=[],
    )


@router.post(
    "/orders/{order_id}/auto-assign",
    response_model=AssignmentResult,
    summary="Auto-assign the best-scoring available agent",
)
def auto_assign(
    order_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    notifier: NotificationService = Depends(get_notification_service),
) -> AssignmentResult:
    service = OrderService(db, notifier)
    order, agent, decision = service.auto_assign(order_id, admin)
    return AssignmentResult(
        agent=_agent_profile(db, agent),
        decision=_scored_out(decision.decision),
        candidates_considered=decision.candidates_considered,
        ranking=[_scored_out(s) for s in decision.ranking],
    )


@router.post(
    "/orders/{order_id}/override",
    response_model=OrderDetail,
    summary="Override an order status (audited, records tracking history)",
)
def override_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    notifier: NotificationService = Depends(get_notification_service),
) -> OrderDetail:
    service = OrderService(db, notifier)
    service.admin_override_status(order_id, data.status, admin, data.reason or "Admin override")
    return OrderDetail.model_validate(service.get_detail_for_actor(order_id, admin))
