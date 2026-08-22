"""Intelligent delivery-agent assignment engine (pure domain logic).

Candidate agents are scored on a weighted combination of proximity, zone match,
current workload and location freshness. The engine never simply picks the
closest or least-loaded agent — it balances all four factors and returns a full,
auditable score breakdown plus a human-readable explanation (used in the UI to
show *why* an agent was selected).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.geo import haversine_km

# Weights sum to 1.0. Distance dominates, then zone match, then workload, then
# how recently the agent reported their location.
W_DISTANCE = 0.40
W_ZONE = 0.30
W_WORKLOAD = 0.20
W_FRESHNESS = 0.10

# Distance beyond this (km) contributes no proximity score.
MAX_EFFECTIVE_DISTANCE_KM = 30.0
# Location older than this (minutes) is considered fully stale.
MAX_LOCATION_AGE_MIN = 60.0
# Neutral score used when a signal is unavailable (e.g. no coordinates).
NEUTRAL = 0.5


@dataclass
class AgentCandidate:
    """Input describing one assignable agent."""

    agent_id: int
    name: str
    zone_id: Optional[int]
    active_orders: int
    max_capacity: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_location_update: Optional[datetime] = None


@dataclass
class ScoredAgent:
    """Result of scoring a candidate."""

    agent_id: int
    name: str
    score: float
    distance_km: Optional[float]
    distance_score: float
    zone_score: float
    workload_score: float
    freshness_score: float
    explanation: str
    breakdown: dict = field(default_factory=dict)


def _distance_score(distance_km: Optional[float]) -> float:
    if distance_km is None:
        return NEUTRAL
    if distance_km >= MAX_EFFECTIVE_DISTANCE_KM:
        return 0.0
    return 1.0 - (distance_km / MAX_EFFECTIVE_DISTANCE_KM)


def _workload_score(active_orders: int, max_capacity: int) -> float:
    if max_capacity <= 0:
        return 0.0
    free_ratio = (max_capacity - active_orders) / max_capacity
    return max(0.0, min(1.0, free_ratio))


def _freshness_score(last_update: Optional[datetime], now: datetime) -> float:
    if last_update is None:
        return 0.0
    if last_update.tzinfo is None:
        last_update = last_update.replace(tzinfo=timezone.utc)
    age_min = (now - last_update).total_seconds() / 60.0
    if age_min <= 0:
        return 1.0
    if age_min >= MAX_LOCATION_AGE_MIN:
        return 0.0
    return 1.0 - (age_min / MAX_LOCATION_AGE_MIN)


def score_candidate(
    candidate: AgentCandidate,
    *,
    pickup_zone_id: int,
    pickup_lat: Optional[float] = None,
    pickup_lon: Optional[float] = None,
    now: Optional[datetime] = None,
) -> ScoredAgent:
    """Compute the weighted assignment score for a single candidate."""
    now = now or datetime.now(timezone.utc)

    distance_km = haversine_km(
        pickup_lat, pickup_lon, candidate.latitude, candidate.longitude
    )
    distance_score = _distance_score(distance_km)
    zone_score = 1.0 if candidate.zone_id == pickup_zone_id else 0.0
    workload_score = _workload_score(candidate.active_orders, candidate.max_capacity)
    freshness_score = _freshness_score(candidate.last_location_update, now)

    score = (
        W_DISTANCE * distance_score
        + W_ZONE * zone_score
        + W_WORKLOAD * workload_score
        + W_FRESHNESS * freshness_score
    )

    zone_txt = "same zone" if zone_score else "different zone"
    dist_txt = f"{distance_km:.1f} km away" if distance_km is not None else "distance unknown"
    explanation = (
        f"{candidate.name} scored {score:.3f} — {dist_txt}, {zone_txt}, "
        f"{candidate.active_orders}/{candidate.max_capacity} active orders."
    )

    return ScoredAgent(
        agent_id=candidate.agent_id,
        name=candidate.name,
        score=round(score, 4),
        distance_km=round(distance_km, 3) if distance_km is not None else None,
        distance_score=round(distance_score, 4),
        zone_score=round(zone_score, 4),
        workload_score=round(workload_score, 4),
        freshness_score=round(freshness_score, 4),
        explanation=explanation,
        breakdown={
            "weights": {
                "distance": W_DISTANCE,
                "zone": W_ZONE,
                "workload": W_WORKLOAD,
                "freshness": W_FRESHNESS,
            },
            "components": {
                "distance_score": round(distance_score, 4),
                "zone_score": round(zone_score, 4),
                "workload_score": round(workload_score, 4),
                "freshness_score": round(freshness_score, 4),
            },
        },
    )


def rank_candidates(
    candidates: List[AgentCandidate],
    *,
    pickup_zone_id: int,
    pickup_lat: Optional[float] = None,
    pickup_lon: Optional[float] = None,
    now: Optional[datetime] = None,
) -> List[ScoredAgent]:
    """Score and rank candidates best-first.

    Ties are broken deterministically by fewer active orders then lower agent id
    so the outcome is stable and reproducible for auditing.
    """
    now = now or datetime.now(timezone.utc)
    scored = [
        score_candidate(
            c,
            pickup_zone_id=pickup_zone_id,
            pickup_lat=pickup_lat,
            pickup_lon=pickup_lon,
            now=now,
        )
        for c in candidates
    ]
    by_id = {c.agent_id: c for c in candidates}
    scored.sort(
        key=lambda s: (-s.score, by_id[s.agent_id].active_orders, s.agent_id)
    )
    return scored
