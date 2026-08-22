"""Delivery-agent management: profiles, availability, location, capacity."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domain.enums import AgentStatus, UserRole
from app.domain.errors import (
    AgentNotFoundError,
    DuplicateResourceError,
)
from app.models.user import AgentLocation, DeliveryAgent, User
from app.schemas.agent import AgentCreate, AgentUpdate


class AgentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_agents(self) -> List[DeliveryAgent]:
        return self.db.query(DeliveryAgent).order_by(DeliveryAgent.id).all()

    def get_agent(self, agent_id: int) -> DeliveryAgent:
        agent = self.db.get(DeliveryAgent, agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent {agent_id} not found.")
        return agent

    def create_agent(self, data: AgentCreate) -> DeliveryAgent:
        if self.db.query(User).filter(User.email == data.email.lower()).first():
            raise DuplicateResourceError("An account with this email already exists.")
        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            role=UserRole.DELIVERY_AGENT,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        agent = DeliveryAgent(
            user_id=user.id,
            status=AgentStatus.OFFLINE,
            current_zone_id=data.current_zone_id,
            max_active_orders=data.max_active_orders,
            active_orders=0,
            is_active=True,
        )
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def update_agent(self, agent_id: int, data: AgentUpdate) -> DeliveryAgent:
        agent = self.get_agent(agent_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(agent, field, value)
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def set_availability(self, agent: DeliveryAgent, status: AgentStatus) -> DeliveryAgent:
        agent.status = status
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def update_location(
        self, agent: DeliveryAgent, latitude: float, longitude: float
    ) -> DeliveryAgent:
        now = datetime.now(timezone.utc)
        agent.current_latitude = latitude
        agent.current_longitude = longitude
        agent.last_location_update = now
        self.db.add(
            AgentLocation(
                agent_id=agent.id,
                latitude=latitude,
                longitude=longitude,
                recorded_at=now,
            )
        )
        self.db.commit()
        self.db.refresh(agent)
        return agent

    # --- Capacity / status bookkeeping (called by the order service) ---
    def engage(self, agent: DeliveryAgent) -> None:
        """Reserve one capacity slot; flip to BUSY when full."""
        agent.active_orders += 1
        if agent.active_orders >= agent.max_active_orders and agent.status == AgentStatus.AVAILABLE:
            agent.status = AgentStatus.BUSY

    def release(self, agent: DeliveryAgent) -> None:
        """Free one capacity slot; flip BUSY back to AVAILABLE when there is room."""
        agent.active_orders = max(0, agent.active_orders - 1)
        if agent.status == AgentStatus.BUSY and agent.active_orders < agent.max_active_orders:
            agent.status = AgentStatus.AVAILABLE
