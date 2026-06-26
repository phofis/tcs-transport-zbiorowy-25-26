from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_000
WALK_SPEED_M_PER_MIN = 83  # ~5 km/h
MAX_WALK_MINS = 30
MAX_WALK_DISTANCE_M = MAX_WALK_MINS * WALK_SPEED_M_PER_MIN  # 2500 m


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def walk_duration_seconds(distance_m: float) -> int:
    return round(distance_m / WALK_SPEED_M_PER_MIN * 60)
