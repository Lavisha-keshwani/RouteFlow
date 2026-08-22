"""Unit tests for the auto-assignment scoring engine (pure domain logic)."""
from datetime import datetime, timezone

from app.domain.assignment import AgentCandidate, rank_candidates, score_candidate


NOW = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
PICKUP = (13.0000, 80.0000)


def _agent(agent_id, lat, active, zone_id=1, max_cap=5):
    return AgentCandidate(
        agent_id=agent_id,
        name=f"Agent {agent_id}",
        zone_id=zone_id,
        active_orders=active,
        max_capacity=max_cap,
        latitude=lat,
        longitude=80.0000,
        last_location_update=NOW,
    )


class TestScoring:
    def test_does_not_blindly_pick_closest_when_overloaded(self):
        # Agent C is closest (1.1km) but nearly full; Agent A is balanced.
        agent_c = _agent("C", 13.0100, active=5, zone_id=1)  # ~1.1 km, workload 0
        agent_a = _agent("A", 13.0190, active=2, zone_id=1)  # ~2.1 km, workload 0.6
        agent_b = _agent("B", 13.0430, active=1, zone_id=2)  # ~4.8 km, different zone

        ranking = rank_candidates(
            [agent_c, agent_a, agent_b],
            pickup_zone_id=1,
            pickup_lat=PICKUP[0],
            pickup_lon=PICKUP[1],
            now=NOW,
        )
        assert ranking[0].agent_id == "A"
        assert ranking[-1].agent_id == "B"

    def test_same_zone_outranks_different_zone_when_otherwise_equal(self):
        same = _agent("same", 13.0100, active=2, zone_id=1)
        diff = _agent("diff", 13.0100, active=2, zone_id=99)
        ranking = rank_candidates(
            [diff, same], pickup_zone_id=1, pickup_lat=PICKUP[0], pickup_lon=PICKUP[1], now=NOW
        )
        assert ranking[0].agent_id == "same"

    def test_missing_coordinates_use_neutral_distance(self):
        candidate = AgentCandidate(
            agent_id="x", name="x", zone_id=1, active_orders=0, max_capacity=5
        )
        scored = score_candidate(candidate, pickup_zone_id=1, now=NOW)
        assert scored.distance_km is None
        assert 0 < scored.score <= 1

    def test_explanation_is_populated(self):
        scored = score_candidate(_agent("A", 13.01, 1), pickup_zone_id=1, now=NOW)
        assert "Agent A" in scored.explanation
        assert scored.breakdown["weights"]["distance"] == 0.40

    def test_ranking_is_deterministic_on_ties(self):
        a = _agent(1, 13.01, active=1, zone_id=1)
        b = _agent(2, 13.01, active=1, zone_id=1)
        ranking = rank_candidates(
            [b, a], pickup_zone_id=1, pickup_lat=PICKUP[0], pickup_lon=PICKUP[1], now=NOW
        )
        # identical scores -> lower agent id first
        assert [r.agent_id for r in ranking] == [1, 2]
