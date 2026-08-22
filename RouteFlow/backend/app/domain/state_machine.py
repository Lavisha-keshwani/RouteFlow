"""Order status state machine.

A single source of truth for legal order-status transitions. Every status
change in the system is validated here so invalid transitions (e.g.
``DELIVERED -> PICKED_UP``) are impossible, whether triggered by a customer,
an agent, or an admin override.
"""
from __future__ import annotations

from typing import Dict, Set

from app.domain.enums import OrderStatus

# Allowed forward transitions for the normal delivery lifecycle.
_TRANSITIONS: Dict[OrderStatus, Set[OrderStatus]] = {
    OrderStatus.PENDING_CONFIRMATION: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.ASSIGNED, OrderStatus.CANCELLED},
    OrderStatus.ASSIGNED: {OrderStatus.PICKED_UP, OrderStatus.CANCELLED},
    OrderStatus.PICKED_UP: {OrderStatus.IN_TRANSIT},
    OrderStatus.IN_TRANSIT: {OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED, OrderStatus.FAILED},
    OrderStatus.FAILED: {OrderStatus.RESCHEDULED, OrderStatus.CANCELLED},
    OrderStatus.RESCHEDULED: {OrderStatus.ASSIGNED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}

# Terminal states — an order in one of these states cannot transition further
# through the normal flow.
TERMINAL_STATES: Set[OrderStatus] = {OrderStatus.DELIVERED, OrderStatus.CANCELLED}

# Statuses an agent is permitted to set directly.
AGENT_SETTABLE_STATES: Set[OrderStatus] = {
    OrderStatus.PICKED_UP,
    OrderStatus.IN_TRANSIT,
    OrderStatus.OUT_FOR_DELIVERY,
    OrderStatus.DELIVERED,
    OrderStatus.FAILED,
}


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    """Return ``True`` if ``current -> target`` is a valid transition."""
    return target in _TRANSITIONS.get(current, set())


def allowed_transitions(current: OrderStatus) -> Set[OrderStatus]:
    """Return the set of statuses reachable from ``current`` in one step."""
    return set(_TRANSITIONS.get(current, set()))


def is_terminal(status: OrderStatus) -> bool:
    """Return ``True`` if the status is terminal."""
    return status in TERMINAL_STATES
