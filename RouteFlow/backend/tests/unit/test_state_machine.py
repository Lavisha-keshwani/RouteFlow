"""Unit tests for the order status state machine (pure domain logic)."""
import pytest

from app.domain.enums import OrderStatus as S
from app.domain.state_machine import (
    allowed_transitions,
    can_transition,
    is_terminal,
)


VALID = [
    (S.PENDING_CONFIRMATION, S.CONFIRMED),
    (S.CONFIRMED, S.ASSIGNED),
    (S.ASSIGNED, S.PICKED_UP),
    (S.PICKED_UP, S.IN_TRANSIT),
    (S.IN_TRANSIT, S.OUT_FOR_DELIVERY),
    (S.OUT_FOR_DELIVERY, S.DELIVERED),
    (S.OUT_FOR_DELIVERY, S.FAILED),
    (S.FAILED, S.RESCHEDULED),
    (S.RESCHEDULED, S.ASSIGNED),
]

INVALID = [
    (S.DELIVERED, S.PICKED_UP),
    (S.PICKED_UP, S.CONFIRMED),
    (S.DELIVERED, S.IN_TRANSIT),
    (S.PENDING_CONFIRMATION, S.DELIVERED),
    (S.CONFIRMED, S.OUT_FOR_DELIVERY),
    (S.IN_TRANSIT, S.DELIVERED),
]


@pytest.mark.parametrize("current,target", VALID)
def test_valid_transitions(current, target):
    assert can_transition(current, target)


@pytest.mark.parametrize("current,target", INVALID)
def test_invalid_transitions(current, target):
    assert not can_transition(current, target)


def test_terminal_states_have_no_transitions():
    assert is_terminal(S.DELIVERED)
    assert is_terminal(S.CANCELLED)
    assert allowed_transitions(S.DELIVERED) == set()


def test_in_transit_to_out_for_delivery_is_valid():
    assert can_transition(S.IN_TRANSIT, S.OUT_FOR_DELIVERY)
