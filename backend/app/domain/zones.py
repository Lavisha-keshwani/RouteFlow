"""Zone detection helpers (pure text logic).

The base implementation resolves a zone from a free-text address using an
admin-managed Area → Zone mapping. Address text is normalised (lower-cased,
punctuation stripped, whitespace collapsed) before matching so that
``"12 Gandhi Road, Velachery"`` resolves to the *Velachery* area.

The DB-backed lookup lives in the zone service; this module keeps the matching
algorithm pure and unit-testable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Lower-case, strip punctuation and collapse whitespace."""
    if not text:
        return ""
    lowered = text.lower()
    no_punct = _PUNCT_RE.sub(" ", lowered)
    return _WS_RE.sub(" ", no_punct).strip()


@dataclass(frozen=True)
class AreaAlias:
    """A normalisable area candidate for matching."""

    area_id: int
    zone_id: int
    name: str


@dataclass(frozen=True)
class AreaMatch:
    area_id: int
    zone_id: int
    matched_name: str


def match_area(address: str, areas: List[AreaAlias]) -> Optional[AreaMatch]:
    """Find the best area whose name appears in the (normalised) address.

    Longer area names win when several match, so "Anna Nagar West" is preferred
    over "Anna Nagar". Returns ``None`` when no area can be matched — callers
    must surface a clear error rather than silently guessing a zone.
    """
    normalized_address = normalize_text(address)
    if not normalized_address:
        return None

    padded = f" {normalized_address} "
    best: Optional[AreaMatch] = None
    best_len = -1

    for area in areas:
        normalized_name = normalize_text(area.name)
        if not normalized_name:
            continue
        if f" {normalized_name} " in padded:
            if len(normalized_name) > best_len:
                best = AreaMatch(area.area_id, area.zone_id, area.name)
                best_len = len(normalized_name)

    return best
