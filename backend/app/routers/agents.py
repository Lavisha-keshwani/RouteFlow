"""Delivery-agent self-service routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_agent, get_current_user
from app.models.user import DeliveryAgent, User
from app.schemas.agent import AgentProfile, AvailabilityUpdate, LocationUpdate
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


def _to_profile(agent: DeliveryAgent, user: User) -> AgentProfile:
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
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
    )


@router.get("/me", response_model=AgentProfile, summary="Current agent profile")
def my_profile(
    agent: DeliveryAgent = Depends(get_current_agent),
    user: User = Depends(get_current_user),
) -> AgentProfile:
    return _to_profile(agent, user)


@router.patch(
    "/me/availability", response_model=AgentProfile, summary="Update availability status"
)
def update_availability(
    data: AvailabilityUpdate,
    db: Session = Depends(get_db),
    agent: DeliveryAgent = Depends(get_current_agent),
    user: User = Depends(get_current_user),
) -> AgentProfile:
    service = AgentService(db)
    service.set_availability(agent, data.status)
    return _to_profile(agent, user)


@router.patch(
    "/me/location", response_model=AgentProfile, summary="Report current GPS location"
)
def update_location(
    data: LocationUpdate,
    db: Session = Depends(get_db),
    agent: DeliveryAgent = Depends(get_current_agent),
    user: User = Depends(get_current_user),
) -> AgentProfile:
    service = AgentService(db)
    service.update_location(agent, data.latitude, data.longitude)
    return _to_profile(agent, user)
