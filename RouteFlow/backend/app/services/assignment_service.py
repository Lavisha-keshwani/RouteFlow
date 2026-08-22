"""Auto-assignment service (DB-backed) wrapping the domain scoring engine.

Concurrency: candidate agent rows are locked with ``SELECT ... FOR UPDATE`` so
two concurrent assignments cannot push the same agent beyond capacity. Capacity
is re-checked *inside* the locked transaction before the agent is engaged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.assignment import AgentCandidate, ScoredAgent, rank_candidates
from app.domain.enums import AgentStatus
from app.domain.errors import NoAgentAvailableError
from app.models.order import Order
from app.models.user import DeliveryAgent, User


@dataclass
class AssignmentDecision:
    agent: DeliveryAgent
    decision: ScoredAgent
    ranking: List[ScoredAgent]
    candidates_considered: int


class AssignmentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _candidate_query(self, lock: bool):
        query = self.db.query(DeliveryAgent).filter(
            DeliveryAgent.is_active.is_(True),
            DeliveryAgent.status == AgentStatus.AVAILABLE,
            DeliveryAgent.active_orders < DeliveryAgent.max_active_orders,
        )
        if lock:
            query = query.with_for_update()
        return query

    def select_for_order(
        self, order: Order, *, lock: bool = True, exclude_agent_id: Optional[int] = None
    ) -> AssignmentDecision:
        """Pick the best assignable agent for an order's pickup zone.

        Raises :class:`NoAgentAvailableError` if no agent qualifies.
        """
        agents = self._candidate_query(lock).all()
        if exclude_agent_id is not None:
            agents = [a for a in agents if a.id != exclude_agent_id]
        if not agents:
            raise NoAgentAvailableError(
                "No available delivery agent with free capacity was found."
            )

        candidates = [
            AgentCandidate(
                agent_id=a.id,
                name=self._agent_name(a),
                zone_id=a.current_zone_id,
                active_orders=a.active_orders,
                max_capacity=a.max_active_orders,
                latitude=a.current_latitude,
                longitude=a.current_longitude,
                last_location_update=a.last_location_update,
            )
            for a in agents
        ]
        ranking = rank_candidates(
            candidates,
            pickup_zone_id=order.pickup_zone_id,
            pickup_lat=order.pickup_latitude,
            pickup_lon=order.pickup_longitude,
        )
        best = ranking[0]
        agent = next(a for a in agents if a.id == best.agent_id)
        return AssignmentDecision(
            agent=agent,
            decision=best,
            ranking=ranking,
            candidates_considered=len(candidates),
        )

    def _agent_name(self, agent: DeliveryAgent) -> str:
        user = self.db.get(User, agent.user_id)
        return user.full_name if user else f"Agent #{agent.id}"
