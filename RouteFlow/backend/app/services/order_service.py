"""Order service: the orchestrator for the full delivery lifecycle.

Responsibilities:
- Create orders (customer or admin-on-behalf) with an immutable pricing snapshot.
- Idempotent creation via ``Idempotency-Key``.
- Confirm, assign (manual/auto), advance status, fail, reschedule and override.
- Append immutable tracking history on **every** status change.
- Keep agent capacity in sync and fire notifications (isolated from the flow).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.enums import (
    AgentStatus,
    DeliveryAttemptStatus,
    NotificationEvent,
    OrderStatus,
    UserRole,
)
from app.domain.errors import (
    AgentCapacityExceededError,
    AgentUnavailableError,
    ConflictError,
    InvalidStatusTransitionError,
    OrderNotFoundError,
    PermissionDeniedError,
    RescheduleNotAllowedError,
    UnauthorizedOrderAccessError,
    ValidationError,
)
from app.domain.state_machine import (
    AGENT_SETTABLE_STATES,
    can_transition,
)
from app.models.order import DeliveryAttempt, Order, OrderStatusHistory, Package
from app.models.system import IdempotencyKey
from app.models.user import Customer, DeliveryAgent, User
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderCreate
from app.services.agent_service import AgentService
from app.services.assignment_service import AssignmentDecision, AssignmentService
from app.services.audit_service import AuditService
from app.services.pricing_service import PricingService
from app.notifications.service import NotificationService
from app.utils.ids import generate_order_number
from app.utils.logging import get_logger, log_event

logger = get_logger("services.order")

# States in which the assigned agent holds a capacity slot for the order.
_ENGAGED_STATES = {
    OrderStatus.ASSIGNED,
    OrderStatus.PICKED_UP,
    OrderStatus.IN_TRANSIT,
    OrderStatus.OUT_FOR_DELIVERY,
}
_RELEASING_STATES = {OrderStatus.DELIVERED, OrderStatus.FAILED, OrderStatus.CANCELLED}

_STATUS_EVENT = {
    OrderStatus.CONFIRMED: NotificationEvent.ORDER_CONFIRMED,
    OrderStatus.ASSIGNED: NotificationEvent.AGENT_ASSIGNED,
    OrderStatus.PICKED_UP: NotificationEvent.PICKED_UP,
    OrderStatus.IN_TRANSIT: NotificationEvent.IN_TRANSIT,
    OrderStatus.OUT_FOR_DELIVERY: NotificationEvent.OUT_FOR_DELIVERY,
    OrderStatus.DELIVERED: NotificationEvent.DELIVERED,
    OrderStatus.FAILED: NotificationEvent.FAILED,
    OrderStatus.RESCHEDULED: NotificationEvent.RESCHEDULED,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OrderService:
    def __init__(self, db: Session, notifier: Optional[NotificationService] = None) -> None:
        self.db = db
        self.repo = OrderRepository(db)
        self.pricing = PricingService(db)
        self.agents = AgentService(db)
        self.assignment = AssignmentService(db)
        self.audit = AuditService(db)
        self.notifier = notifier or NotificationService(db)

    # ------------------------------------------------------------------ create
    def create_order(
        self,
        data: OrderCreate,
        actor: User,
        *,
        idempotency_key: Optional[str] = None,
        endpoint: str = "POST /api/orders",
    ) -> Order:
        # Idempotent replay: return the previously created order for this key.
        if idempotency_key:
            existing = (
                self.db.query(IdempotencyKey)
                .filter(
                    IdempotencyKey.key == idempotency_key,
                    IdempotencyKey.endpoint == endpoint,
                )
                .first()
            )
            if existing and existing.response_order_id:
                found = self.repo.get(existing.response_order_id)
                if found:
                    return found

        customer = self._resolve_customer(data, actor)
        breakdown, pickup_zone, drop_zone, pickup_area, drop_area = self.pricing.compute(data)

        order = Order(
            order_number="PENDING",
            customer_id=customer.id,
            created_by_user_id=actor.id,
            pickup_address=data.pickup_address,
            drop_address=data.drop_address,
            pickup_area_id=pickup_area.id,
            drop_area_id=drop_area.id,
            pickup_zone_id=pickup_zone.id,
            drop_zone_id=drop_zone.id,
            order_type=data.order_type,
            payment_type=data.payment_type,
            zone_type=breakdown.zone_type,
            status=OrderStatus.PENDING_CONFIRMATION,
            chargeable_weight_kg=breakdown.chargeable_weight,
            base_charge=breakdown.base_charge,
            cod_surcharge=breakdown.cod_surcharge,
            total_charge=breakdown.total_charge,
            currency=breakdown.currency,
            rate_card_id=breakdown.rate_card_id,
        )
        self.db.add(order)
        self.db.flush()
        order.order_number = generate_order_number(order.id, order.created_at or _now())

        self.db.add(
            Package(
                order_id=order.id,
                length_cm=data.length_cm,
                width_cm=data.width_cm,
                height_cm=data.height_cm,
                actual_weight_kg=data.actual_weight_kg,
                volumetric_weight_kg=breakdown.volumetric_weight,
                chargeable_weight_kg=breakdown.chargeable_weight,
            )
        )
        self._append_history(order, None, OrderStatus.PENDING_CONFIRMATION, actor)

        if idempotency_key:
            self.db.add(
                IdempotencyKey(
                    key=idempotency_key,
                    endpoint=endpoint,
                    user_id=actor.id,
                    response_order_id=order.id,
                    created_at=_now(),
                )
            )
        if actor.role == UserRole.ADMIN:
            self.audit.record(
                actor=actor,
                action="ORDER_CREATED_ON_BEHALF",
                entity_type="order",
                entity_id=order.id,
                new_value={"customer_id": customer.id, "total": str(order.total_charge)},
            )

        self.db.commit()
        self.db.refresh(order)
        log_event(logger, "order_created", order_id=order.id, order_number=order.order_number)
        return order

    # ------------------------------------------------------------------ confirm
    def confirm_order(self, order_id: int, actor: User) -> Order:
        order = self._get_owned(order_id, actor)
        if order.status != OrderStatus.PENDING_CONFIRMATION:
            raise InvalidStatusTransitionError(
                "Only pending orders can be confirmed.",
                details={"current_status": order.status.value},
            )
        self._transition(order, OrderStatus.CONFIRMED, actor)
        order.confirmed_at = _now()
        self.db.commit()
        self.db.refresh(order)
        self._notify(order, OrderStatus.CONFIRMED)
        self.db.commit()
        return order

    # -------------------------------------------------------------- assignment
    def assign_agent_manual(
        self, order_id: int, agent_id: int, actor: User, reason: Optional[str] = None
    ) -> Tuple[Order, DeliveryAgent, Optional[dict]]:
        order = self._get_or_404(order_id)
        self._assert_assignable_state(order)

        agent = (
            self.db.query(DeliveryAgent)
            .filter(DeliveryAgent.id == agent_id)
            .with_for_update()
            .first()
        )
        if agent is None:
            raise OrderNotFoundError(f"Agent {agent_id} not found.", code="AGENT_NOT_FOUND")
        if not agent.is_active or agent.status == AgentStatus.OFFLINE:
            raise AgentUnavailableError("Selected agent is not available.")
        if not agent.has_capacity:
            raise AgentCapacityExceededError("Selected agent is at maximum capacity.")

        previous_agent_id = order.assigned_agent_id
        self._engage_and_assign(order, agent, actor, score=None, metadata={
            "assigned_by": actor.role.value,
            "manual": True,
            "reason": reason,
            "previous_agent": previous_agent_id,
        })
        self.audit.record(
            actor=actor,
            action="AGENT_ASSIGNED_MANUAL",
            entity_type="order",
            entity_id=order.id,
            old_value={"previous_agent": previous_agent_id},
            new_value={"new_agent": agent.id, "reason": reason},
        )
        self.db.commit()
        self.db.refresh(order)
        self._notify(order, OrderStatus.ASSIGNED)
        self.db.commit()
        return order, agent, None

    def auto_assign(
        self, order_id: int, actor: User
    ) -> Tuple[Order, DeliveryAgent, AssignmentDecision]:
        order = self._get_or_404(order_id)
        self._assert_assignable_state(order)

        decision = self.assignment.select_for_order(order, lock=True)
        agent = decision.agent
        self._engage_and_assign(
            order,
            agent,
            actor,
            score=decision.decision.score,
            metadata={
                "assigned_by": "AUTO",
                "manual": False,
                "score": decision.decision.score,
                "explanation": decision.decision.explanation,
                "candidates_considered": decision.candidates_considered,
                "breakdown": decision.decision.breakdown,
            },
        )
        self.audit.record(
            actor=actor,
            action="AGENT_ASSIGNED_AUTO",
            entity_type="order",
            entity_id=order.id,
            new_value={
                "agent_id": agent.id,
                "score": decision.decision.score,
                "explanation": decision.decision.explanation,
            },
        )
        self.db.commit()
        self.db.refresh(order)
        self._notify(order, OrderStatus.ASSIGNED)
        self.db.commit()
        log_event(
            logger,
            "order_auto_assigned",
            order_id=order.id,
            agent_id=agent.id,
            score=decision.decision.score,
        )
        return order, agent, decision

    def _engage_and_assign(
        self,
        order: Order,
        agent: DeliveryAgent,
        actor: User,
        *,
        score: Optional[float],
        metadata: Optional[dict],
    ) -> None:
        # Release a previously assigned agent (manual reassignment) before engaging.
        if order.assigned_agent_id and order.assigned_agent_id != agent.id:
            prev = self.db.get(DeliveryAgent, order.assigned_agent_id)
            if prev and order.status in _ENGAGED_STATES:
                self.agents.release(prev)

        self.agents.engage(agent)
        order.assigned_agent_id = agent.id
        self._transition(order, OrderStatus.ASSIGNED, actor, reason=None, metadata=metadata)

        attempt = self._current_open_attempt(order)
        if attempt is None:
            attempt = self._new_attempt(order)
        attempt.agent_id = agent.id
        attempt.status = DeliveryAttemptStatus.IN_PROGRESS
        attempt.assignment_score = score
        attempt.assignment_metadata = metadata

    # ----------------------------------------------------------- status update
    def update_status(
        self, order_id: int, new_status: OrderStatus, actor: User, reason: Optional[str] = None
    ) -> Order:
        order = self._get_or_404(order_id)
        self._authorize_status_actor(order, actor, new_status)

        if not can_transition(order.status, new_status):
            raise InvalidStatusTransitionError(
                f"Cannot move order from {order.status.value} to {new_status.value}.",
                details={"from": order.status.value, "to": new_status.value},
            )

        self._transition(order, new_status, actor, reason=reason)
        if new_status == OrderStatus.DELIVERED:
            order.delivered_at = _now()
            self._close_attempt(order, DeliveryAttemptStatus.DELIVERED)
        self.db.commit()
        self.db.refresh(order)
        if new_status in _STATUS_EVENT:
            self._notify(order, new_status)
            self.db.commit()
        return order

    # -------------------------------------------------------------- fail flow
    def fail_delivery(
        self, order_id: int, failure_reason, actor: User, notes: Optional[str] = None
    ) -> Order:
        order = self._get_or_404(order_id)
        self._authorize_status_actor(order, actor, OrderStatus.FAILED)
        if not can_transition(order.status, OrderStatus.FAILED):
            raise InvalidStatusTransitionError(
                f"Order in {order.status.value} cannot be marked failed.",
                details={"current_status": order.status.value},
            )

        attempt = self._current_open_attempt(order)
        if attempt is not None:
            attempt.status = DeliveryAttemptStatus.FAILED
            attempt.failure_reason = failure_reason
            attempt.notes = notes
        self._transition(
            order,
            OrderStatus.FAILED,
            actor,
            reason=notes,
            metadata={"failure_reason": failure_reason.value},
        )
        self.db.commit()
        self.db.refresh(order)
        self._notify(order, OrderStatus.FAILED, context={"reason": failure_reason.value})
        self.db.commit()
        log_event(logger, "delivery_failed", order_id=order.id, reason=failure_reason.value)
        return order

    # -------------------------------------------------------------- reschedule
    def reschedule(
        self,
        order_id: int,
        actor: User,
        *,
        new_date: date,
        time_window: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Order:
        order = self._get_owned(order_id, actor)
        if order.status != OrderStatus.FAILED:
            raise RescheduleNotAllowedError(
                "Only failed deliveries can be rescheduled.",
                details={"current_status": order.status.value},
            )
        failed_attempts = [
            a for a in order.attempts if a.status == DeliveryAttemptStatus.FAILED
        ]
        if len(failed_attempts) >= settings.MAX_RESCHEDULE_ATTEMPTS:
            raise RescheduleNotAllowedError(
                f"Maximum of {settings.MAX_RESCHEDULE_ATTEMPTS} reschedule attempts reached."
            )

        previous_agent_id = order.assigned_agent_id
        self._transition(order, OrderStatus.RESCHEDULED, actor, reason=reason)
        order.assigned_agent_id = None

        # Create a fresh delivery attempt rather than mutating history.
        attempt = self._new_attempt(order)
        attempt.scheduled_date = new_date
        attempt.time_window = time_window
        attempt.reschedule_reason = reason
        attempt.status = DeliveryAttemptStatus.SCHEDULED
        self.db.flush()

        self._notify(order, OrderStatus.RESCHEDULED, context={"date": new_date.isoformat()})

        # Auto-assign a new agent, preferring someone other than the failed one.
        try:
            decision = self.assignment.select_for_order(
                order, lock=True, exclude_agent_id=previous_agent_id
            )
        except Exception:
            decision = self.assignment.select_for_order(order, lock=True)

        agent = decision.agent
        self.agents.engage(agent)
        order.assigned_agent_id = agent.id
        self._transition(
            order,
            OrderStatus.ASSIGNED,
            actor,
            metadata={
                "assigned_by": "AUTO_RESCHEDULE",
                "score": decision.decision.score,
                "explanation": decision.decision.explanation,
                "previous_agent": previous_agent_id,
            },
        )
        attempt.agent_id = agent.id
        attempt.status = DeliveryAttemptStatus.IN_PROGRESS
        attempt.assignment_score = decision.decision.score
        attempt.assignment_metadata = {"explanation": decision.decision.explanation}

        self.db.commit()
        self.db.refresh(order)
        self._notify(order, OrderStatus.ASSIGNED)
        self.db.commit()
        log_event(logger, "order_rescheduled", order_id=order.id, new_agent=agent.id)
        return order

    # ---------------------------------------------------------- admin override
    def admin_override_status(
        self, order_id: int, new_status: OrderStatus, actor: User, reason: str
    ) -> Order:
        if actor.role != UserRole.ADMIN:
            raise PermissionDeniedError("Only admins may override order status.")
        if not reason:
            raise ValidationError("An override reason is required.")
        order = self._get_or_404(order_id)
        old_status = order.status

        # Controlled override: bypass the state machine but always record it.
        self._transition(
            order,
            new_status,
            actor,
            reason=reason,
            metadata={"override": True, "from": old_status.value},
            validate=False,
        )
        if new_status == OrderStatus.DELIVERED:
            order.delivered_at = _now()
            self._close_attempt(order, DeliveryAttemptStatus.DELIVERED)
        self.audit.record(
            actor=actor,
            action="STATUS_OVERRIDE",
            entity_type="order",
            entity_id=order.id,
            old_value={"status": old_status.value},
            new_value={"status": new_status.value, "reason": reason},
        )
        self.db.commit()
        self.db.refresh(order)
        if new_status in _STATUS_EVENT:
            self._notify(order, new_status)
            self.db.commit()
        return order

    # ------------------------------------------------------------------ reads
    def get_detail_for_actor(self, order_id: int, actor: User) -> Order:
        order = self.repo.get_detail(order_id)
        if order is None:
            raise OrderNotFoundError(f"Order {order_id} not found.")
        self._assert_can_view(order, actor)
        return order

    def list_orders(self, actor: User, **filters) -> Tuple[List[Order], int]:
        """List orders scoped to the actor's role."""
        if actor.role == UserRole.CUSTOMER:
            customer = self._customer_for_user(actor)
            filters["customer_id"] = customer.id
        elif actor.role == UserRole.DELIVERY_AGENT:
            agent = self._agent_for_user(actor)
            filters["agent_id"] = agent.id
        return self.repo.list(**filters)

    # --------------------------------------------------------------- internals
    def _transition(
        self,
        order: Order,
        new_status: OrderStatus,
        actor: Optional[User],
        *,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
        validate: bool = True,
    ) -> None:
        old = order.status
        if validate and old != new_status and not can_transition(old, new_status):
            raise InvalidStatusTransitionError(
                f"Cannot move order from {old.value} to {new_status.value}."
            )
        if old in _ENGAGED_STATES and new_status in _RELEASING_STATES:
            self._release_assigned_agent(order)
        order.status = new_status
        self._append_history(order, old, new_status, actor, reason, metadata)

    def _append_history(
        self,
        order: Order,
        old: Optional[OrderStatus],
        new: OrderStatus,
        actor: Optional[User],
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        self.db.add(
            OrderStatusHistory(
                order_id=order.id,
                old_status=old,
                new_status=new,
                actor_id=actor.id if actor else None,
                actor_role=actor.role if actor else None,
                reason=reason,
                event_metadata=metadata,
                created_at=_now(),
            )
        )

    def _release_assigned_agent(self, order: Order) -> None:
        if not order.assigned_agent_id:
            return
        agent = self.db.get(DeliveryAgent, order.assigned_agent_id)
        if agent:
            self.agents.release(agent)

    def _new_attempt(self, order: Order) -> DeliveryAttempt:
        next_number = 1 + len(order.attempts)
        attempt = DeliveryAttempt(
            order_id=order.id,
            attempt_number=next_number,
            status=DeliveryAttemptStatus.SCHEDULED,
        )
        self.db.add(attempt)
        self.db.flush()
        order.attempts.append(attempt)
        return attempt

    def _current_open_attempt(self, order: Order) -> Optional[DeliveryAttempt]:
        for attempt in reversed(order.attempts):
            if attempt.status in (
                DeliveryAttemptStatus.SCHEDULED,
                DeliveryAttemptStatus.IN_PROGRESS,
            ):
                return attempt
        return None

    def _close_attempt(self, order: Order, status: DeliveryAttemptStatus) -> None:
        attempt = self._current_open_attempt(order)
        if attempt is not None:
            attempt.status = status

    def _notify(self, order: Order, status: OrderStatus, context: Optional[dict] = None) -> None:
        event = _STATUS_EVENT.get(status)
        if event is None:
            return
        email, phone = self._customer_contact(order)
        ctx = {"currency": order.currency, "total": str(order.total_charge)}
        if context:
            ctx.update(context)
        self.notifier.notify(
            order_id=order.id,
            order_number=order.order_number,
            event=event,
            recipient_email=email,
            recipient_phone=phone,
            context=ctx,
        )

    # --- resolution & authorization helpers ---
    def _resolve_customer(self, data: OrderCreate, actor: User) -> Customer:
        if actor.role == UserRole.ADMIN:
            if not data.customer_id:
                raise ValidationError("customer_id is required when an admin creates an order.")
            customer = self.db.get(Customer, data.customer_id)
            if customer is None:
                raise OrderNotFoundError(
                    f"Customer {data.customer_id} not found.", code="CUSTOMER_NOT_FOUND"
                )
            return customer
        if actor.role == UserRole.CUSTOMER:
            return self._customer_for_user(actor)
        raise PermissionDeniedError("Only customers or admins can create orders.")

    def _customer_for_user(self, user: User) -> Customer:
        customer = self.db.query(Customer).filter(Customer.user_id == user.id).first()
        if customer is None:
            raise PermissionDeniedError("No customer profile for this user.")
        return customer

    def _agent_for_user(self, user: User) -> DeliveryAgent:
        agent = self.db.query(DeliveryAgent).filter(DeliveryAgent.user_id == user.id).first()
        if agent is None:
            raise PermissionDeniedError("No agent profile for this user.")
        return agent

    def _get_or_404(self, order_id: int) -> Order:
        order = self.repo.get_detail(order_id)
        if order is None:
            raise OrderNotFoundError(f"Order {order_id} not found.")
        return order

    def _get_owned(self, order_id: int, actor: User) -> Order:
        order = self._get_or_404(order_id)
        self._assert_can_view(order, actor)
        return order

    def _assert_can_view(self, order: Order, actor: User) -> None:
        if actor.role == UserRole.ADMIN:
            return
        if actor.role == UserRole.CUSTOMER:
            customer = self._customer_for_user(actor)
            if order.customer_id != customer.id:
                raise UnauthorizedOrderAccessError("You cannot access this order.")
            return
        if actor.role == UserRole.DELIVERY_AGENT:
            agent = self._agent_for_user(actor)
            if order.assigned_agent_id != agent.id:
                raise UnauthorizedOrderAccessError("This order is not assigned to you.")
            return
        raise PermissionDeniedError("Access denied.")

    def _authorize_status_actor(
        self, order: Order, actor: User, new_status: OrderStatus
    ) -> None:
        if actor.role == UserRole.ADMIN:
            return
        if actor.role == UserRole.DELIVERY_AGENT:
            agent = self._agent_for_user(actor)
            if order.assigned_agent_id != agent.id:
                raise UnauthorizedOrderAccessError("This order is not assigned to you.")
            if new_status not in AGENT_SETTABLE_STATES:
                raise PermissionDeniedError(
                    f"Agents cannot set status {new_status.value}."
                )
            return
        raise PermissionDeniedError("You cannot update this order's status.")

    def _assert_assignable_state(self, order: Order) -> None:
        if order.status not in (OrderStatus.CONFIRMED, OrderStatus.RESCHEDULED):
            raise ConflictError(
                "Order must be confirmed (or rescheduled) before assignment.",
                code="ORDER_NOT_ASSIGNABLE",
                details={"current_status": order.status.value},
            )

    def _customer_contact(self, order: Order) -> Tuple[str, Optional[str]]:
        customer = self.db.get(Customer, order.customer_id)
        user = self.db.get(User, customer.user_id) if customer else None
        if user is None:
            return settings.EMAIL_FROM, None
        return user.email, user.phone
