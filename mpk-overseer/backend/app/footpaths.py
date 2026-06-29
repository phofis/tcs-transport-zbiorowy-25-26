from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from app.geo import haversine_m, walk_duration_seconds
from app.models import Stop

logger = logging.getLogger(__name__)

DEFAULT_FOOTPATHS_PATH = Path(__file__).resolve().parent.parent / "data" / "footpaths.json"


@dataclass(frozen=True)
class Footpath:
    target: str
    duration_seconds: int


FootpathMap = dict[str, list[Footpath]]


def load_footpaths(path: Path | None = None) -> FootpathMap:
    target_path = path or DEFAULT_FOOTPATHS_PATH
    if not target_path.is_file():
        if target_path == DEFAULT_FOOTPATHS_PATH:
            logger.info("Footpaths file not found at %s — generating", target_path)
            from scripts.precompute_footpaths import main as precompute_footpaths

            precompute_footpaths()
        if not target_path.is_file():
            logger.warning(
                "Footpaths file not found at %s — walking transfers disabled",
                target_path,
            )
            return {}

    with target_path.open(encoding="utf-8") as fh:
        raw: dict[str, list[dict[str, int | str]]] = json.load(fh)

    footpaths: FootpathMap = {}
    for source_id, edges in raw.items():
        footpaths[source_id] = [
            Footpath(target=str(edge["target"]), duration_seconds=int(edge["duration_seconds"]))
            for edge in edges
        ]
    logger.info("Loaded footpaths for %d stops from %s", len(footpaths), target_path)
    return footpaths


def walk_edges_from_point(
    lat: float,
    lng: float,
    stops: dict[str, Stop],
    max_walk_seconds: int,
) -> list[tuple[str, int]]:
    """Walking edges from an arbitrary coordinate to nearby stops."""
    edges: list[tuple[str, int]] = []
    for stop_id, stop in stops.items():
        distance_m = haversine_m(lat, lng, stop.lat, stop.lng)
        if distance_m <= 0:
            continue
        duration = walk_duration_seconds(distance_m)
        if duration <= max_walk_seconds:
            edges.append((stop_id, duration))
    return edges


def footpaths_within_limit(
    footpaths: FootpathMap,
    stop_id: str,
    max_walk_seconds: int,
) -> list[tuple[str, int]]:
    return [
        (edge.target, edge.duration_seconds)
        for edge in footpaths.get(stop_id, [])
        if edge.duration_seconds <= max_walk_seconds
    ]
