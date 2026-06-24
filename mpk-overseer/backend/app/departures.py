from __future__ import annotations

import re
import time

from app.blocks import ConnectionStore
from app.gtfs_loader import GtfsData
from app.models import Connection, DepartureOut, LineDeparturesOut, StopDeparturesOut, StopKind

HORIZON_STOP = 4 * 3600
MAX_PER_LINE = 5


def _route_kind(route_type: int) -> StopKind:
    if route_type == 0:
        return "tram"
    if route_type == 3:
        return "bus"
    return "bus"


def _natural_sort_key(value: str) -> list[int | str]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def _line_kind(gtfs: GtfsData, line: str) -> StopKind:
    kinds: set[StopKind] = set()
    for trip in gtfs.trips.values():
        route = gtfs.routes.get(trip.route_id)
        if route is None or route.route_short_name != line:
            continue
        kinds.add(_route_kind(route.route_type))
    if "tram" in kinds and "bus" in kinds:
        return "mixed"
    if "tram" in kinds:
        return "tram"
    if "bus" in kinds:
        return "bus"
    return "bus"


def get_stop_departures(
    store: ConnectionStore,
    gtfs: GtfsData,
    stop_id: str,
    now_ts: int | None = None,
) -> StopDeparturesOut:
    now = int(now_ts if now_ts is not None else time.time())
    horizon_end = now + HORIZON_STOP

    grouped: dict[str, list[Connection]] = {}
    for block in store.snapshot():
        for connection in block.connections:
            if connection.departure_stop != stop_id:
                continue
            if connection.departure_ts < now or connection.departure_ts > horizon_end:
                continue
            grouped.setdefault(connection.route_short_name, []).append(connection)

    lines: list[LineDeparturesOut] = []
    for line in sorted(grouped, key=_natural_sort_key):
        departures = sorted(grouped[line], key=lambda connection: connection.departure_ts)[
            :MAX_PER_LINE
        ]
        lines.append(
            LineDeparturesOut(
                line=line,
                kind=_line_kind(gtfs, line),
                departures=[
                    DepartureOut(
                        departure_ts=connection.departure_ts,
                        trip_id=connection.trip_id,
                        headsign=connection.trip_headsign,
                    )
                    for connection in departures
                ],
            )
        )

    return StopDeparturesOut(stop_id=stop_id, generated_ts=now, lines=lines)
