"""Geospatial helpers used by the auto-assignment engine."""
from __future__ import annotations

import math
from typing import Optional

EARTH_RADIUS_KM = 6371.0088


def haversine_km(
    lat1: Optional[float],
    lon1: Optional[float],
    lat2: Optional[float],
    lon2: Optional[float],
) -> Optional[float]:
    """Great-circle distance between two points in kilometres.

    Returns ``None`` if any coordinate is missing so callers can degrade
    gracefully when an agent has never reported a location.
    """
    if None in (lat1, lon1, lat2, lon2):
        return None

    phi1 = math.radians(lat1)  # type: ignore[arg-type]
    phi2 = math.radians(lat2)  # type: ignore[arg-type]
    d_phi = math.radians(lat2 - lat1)  # type: ignore[operator]
    d_lambda = math.radians(lon2 - lon1)  # type: ignore[operator]

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c
