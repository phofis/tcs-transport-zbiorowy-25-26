from __future__ import annotations

import time
from dataclasses import dataclass

from app.gtfs_loader import GtfsData
from app.gtfs_time import dates_in_window, parse_gtfs_time, pick_time, to_epoch_utc
from app.models import Connection

HORIZON = 72 * 3600
REGEN_INTERVAL = 4 * 3600
GRACE = 4 * 3600


@dataclass(frozen=True)
class ConnectionBlock:
    start_ts: int
    end_ts: int
    connections: list[Connection]


class ConnectionStore:
    def __init__(self) -> None:
        self._blocks: tuple[ConnectionBlock, ...] = ()

    def snapshot(self) -> tuple[ConnectionBlock, ...]:
        return self._blocks

    def replace(self, blocks: tuple[ConnectionBlock, ...]) -> None:
        self._blocks = blocks


def _trip_connections_for_date(
    gtfs: GtfsData,
    trip_id: str,
    service_date,
) -> list[Connection]:
    trip = gtfs.trips.get(trip_id)
    if trip is None:
        return []

    route = gtfs.routes.get(trip.route_id)
    if route is None:
        return []

    stop_times = gtfs.stop_times_by_trip.get(trip_id)
    if not stop_times or len(stop_times) < 2:
        return []

    connections: list[Connection] = []
    for index in range(len(stop_times) - 1):
        current = stop_times[index]
        nxt = stop_times[index + 1]
        departure_time = pick_time(current.departure_time, current.arrival_time)
        arrival_time = pick_time(nxt.arrival_time, nxt.departure_time)
        if departure_time is None or arrival_time is None:
            continue

        departure_ts = to_epoch_utc(service_date, parse_gtfs_time(departure_time))
        arrival_ts = to_epoch_utc(service_date, parse_gtfs_time(arrival_time))
        connections.append(
            Connection(
                departure_stop=current.stop_id,
                arrival_stop=nxt.stop_id,
                departure_ts=departure_ts,
                arrival_ts=arrival_ts,
                trip_id=trip_id,
                route_short_name=route.route_short_name,
                trip_headsign=trip.trip_headsign,
            )
        )
    return connections


def generate_connections(
    gtfs: GtfsData,
    start_ts: int,
    end_ts: int,
) -> list[Connection]:
    trips_by_service: dict[str, list[str]] = {}
    for trip_id, trip in gtfs.trips.items():
        trips_by_service.setdefault(trip.service_id, []).append(trip_id)

    connections: list[Connection] = []
    for service_date in dates_in_window(start_ts, end_ts):
        for service_id, active_dates in gtfs.service_dates.items():
            if service_date not in active_dates:
                continue
            for trip_id in trips_by_service.get(service_id, []):
                for connection in _trip_connections_for_date(gtfs, trip_id, service_date):
                    if start_ts <= connection.departure_ts <= end_ts:
                        connections.append(connection)

    connections.sort(key=lambda connection: connection.departure_ts)
    return connections


def build_initial_store(gtfs: GtfsData, now_ts: int | None = None) -> ConnectionStore:
    now = int(now_ts if now_ts is not None else time.time())
    end_ts = now + HORIZON
    connections = generate_connections(gtfs, now, end_ts)
    store = ConnectionStore()
    store.replace((ConnectionBlock(start_ts=now, end_ts=end_ts, connections=connections),))
    return store


def regenerate_store(
    store: ConnectionStore,
    gtfs: GtfsData,
    now_ts: int | None = None,
) -> None:
    now = int(now_ts if now_ts is not None else time.time())
    kept_blocks = [block for block in store.snapshot() if block.end_ts >= now - GRACE]
    horizon_end = now + HORIZON

    if kept_blocks:
        max_end = max(block.end_ts for block in kept_blocks)
    else:
        max_end = now

    if max_end < horizon_end:
        new_connections = generate_connections(gtfs, max_end, horizon_end)
        kept_blocks.append(
            ConnectionBlock(start_ts=max_end, end_ts=horizon_end, connections=new_connections)
        )

    store.replace(tuple(sorted(kept_blocks, key=lambda block: block.start_ts)))
