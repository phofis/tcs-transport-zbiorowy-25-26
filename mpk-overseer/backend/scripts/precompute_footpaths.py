"""One-time footpath precompute: all stop pairs within 30 min walk."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.geo import MAX_WALK_DISTANCE_M, haversine_m, walk_duration_seconds
from app.gtfs_loader import load_gtfs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GTFS_DIR = Path(__file__).resolve().parent.parent / "data" / "gtfs"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "footpaths.json"
GTFS_GLOB = "GTFS_KRK_*.zip"


def main() -> None:
    feed_paths = sorted(GTFS_DIR.glob(GTFS_GLOB))
    if not feed_paths:
        raise FileNotFoundError(
            f"No GTFS feeds found in {GTFS_DIR}. Expected files matching {GTFS_GLOB}."
        )

    logger.info("Loading GTFS from %d feed(s)", len(feed_paths))
    gtfs = load_gtfs([str(path) for path in feed_paths])
    stops = list(gtfs.stops.values())
    logger.info("Computing footpaths for %d stops", len(stops))

    footpaths: dict[str, list[dict[str, int | str]]] = {}
    pair_count = 0

    for i, source in enumerate(stops):
        edges: list[dict[str, int | str]] = []
        for j, target in enumerate(stops):
            if i == j:
                continue
            distance_m = haversine_m(source.lat, source.lng, target.lat, target.lng)
            if distance_m <= 0 or distance_m > MAX_WALK_DISTANCE_M:
                continue
            duration = walk_duration_seconds(distance_m)
            edges.append({"target": target.stop_id, "duration_seconds": duration})
            pair_count += 1
        if edges:
            footpaths[source.stop_id] = edges

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(footpaths, fh, ensure_ascii=False, separators=(",", ":"))

    logger.info(
        "Wrote %d stop entries (%d directed edges) to %s",
        len(footpaths),
        pair_count,
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()
