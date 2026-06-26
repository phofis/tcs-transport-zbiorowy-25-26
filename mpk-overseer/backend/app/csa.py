from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.blocks import ConnectionStore
from app.footpaths import FootpathMap, footpaths_within_limit, walk_edges_from_point
from app.geo import haversine_m, walk_duration_seconds
from app.gtfs_loader import GtfsData
from app.models import Connection, RouteLegOut, RouteRequest, RouteResponse, RouteStopOut, Stop
from app.stop_labels import format_stop_display_name

INF = 10**18


@dataclass(frozen=True)
class _WalkOrigin:
    kind: Literal["stop", "point"]
    stop_id: str | None = None
    lat: float | None = None
    lng: float | None = None


@dataclass(frozen=True)
class _WalkPointer:
    origin: _WalkOrigin
    to_stop: str
    duration_seconds: int


@dataclass(frozen=True)
class _TransitPointer:
    connection: Connection


_JourneyPointer = _WalkPointer | _TransitPointer


def _flatten_connections(store: ConnectionStore) -> list[Connection]:
    connections: list[Connection] = []
    for block in store.snapshot():
        connections.extend(block.connections)
    return connections


def _origin_edges(
    request: RouteRequest,
    footpaths: FootpathMap,
    stops: dict[str, Stop],
    max_walk_seconds: int,
) -> tuple[_WalkOrigin, list[tuple[str, int]]]:
    if request.start_stop_id is not None:
        origin = _WalkOrigin(kind="stop", stop_id=request.start_stop_id)
        edges = [(request.start_stop_id, 0)]
        edges.extend(footpaths_within_limit(footpaths, request.start_stop_id, max_walk_seconds))
        return origin, edges

    assert request.start_lat is not None and request.start_lng is not None
    origin = _WalkOrigin(kind="point", lat=request.start_lat, lng=request.start_lng)
    edges = walk_edges_from_point(request.start_lat, request.start_lng, stops, max_walk_seconds)
    return origin, edges


def _relax_footpaths(
    stop_id: str,
    arrival_ts: int,
    footpaths: FootpathMap,
    max_walk_seconds: int,
    earliest_arrival: dict[str, int],
    journey_pointer: dict[str, _JourneyPointer],
) -> None:
    for target, duration in footpaths_within_limit(footpaths, stop_id, max_walk_seconds):
        candidate = arrival_ts + duration
        if candidate < earliest_arrival.get(target, INF):
            earliest_arrival[target] = candidate
            journey_pointer[target] = _WalkPointer(
                origin=_WalkOrigin(kind="stop", stop_id=stop_id),
                to_stop=target,
                duration_seconds=duration,
            )


def _resolve_destination(
    request: RouteRequest,
    stops: dict[str, Stop],
    max_walk_seconds: int,
    earliest_arrival: dict[str, int],
) -> tuple[int, str, int] | None:
    if request.end_stop_id is not None:
        arrival = earliest_arrival.get(request.end_stop_id, INF)
        if arrival >= INF:
            return None
        return arrival, request.end_stop_id, 0

    assert request.end_lat is not None and request.end_lng is not None
    best: tuple[int, str, int] | None = None
    for stop_id, stop in stops.items():
        arrival = earliest_arrival.get(stop_id, INF)
        if arrival >= INF:
            continue
        distance_m = haversine_m(stop.lat, stop.lng, request.end_lat, request.end_lng)
        if distance_m <= 0:
            continue
        walk_seconds = walk_duration_seconds(distance_m)
        if walk_seconds > max_walk_seconds:
            continue
        total = arrival + walk_seconds
        if best is None or total < best[0]:
            best = (total, stop_id, walk_seconds)
    return best


def _stop_label(stops: dict[str, Stop], stop_id: str | None) -> str | None:
    if stop_id is None:
        return None
    stop = stops.get(stop_id)
    if stop is None:
        return stop_id
    return format_stop_display_name(stop)


def _stop_coords(stops: dict[str, Stop], stop_id: str | None) -> tuple[float | None, float | None]:
    if stop_id is None:
        return None, None
    stop = stops.get(stop_id)
    if stop is None:
        return None, None
    return stop.lat, stop.lng


def _build_walk_leg(pointer: _WalkPointer, stops: dict[str, Stop]) -> RouteLegOut:
    origin = pointer.origin
    to_lat, to_lng = _stop_coords(stops, pointer.to_stop)
    if origin.kind == "point":
        return RouteLegOut(
            type="walk",
            from_stop_id=None,
            to_stop_id=pointer.to_stop,
            from_name="Własny punkt",
            to_name=_stop_label(stops, pointer.to_stop),
            from_lat=origin.lat,
            from_lng=origin.lng,
            to_lat=to_lat,
            to_lng=to_lng,
            duration_seconds=pointer.duration_seconds,
        )
    from_lat, from_lng = _stop_coords(stops, origin.stop_id)
    return RouteLegOut(
        type="walk",
        from_stop_id=origin.stop_id,
        to_stop_id=pointer.to_stop,
        from_name=_stop_label(stops, origin.stop_id),
        to_name=_stop_label(stops, pointer.to_stop),
        from_lat=from_lat,
        from_lng=from_lng,
        to_lat=to_lat,
        to_lng=to_lng,
        duration_seconds=pointer.duration_seconds,
    )


def _to_route_stop(stops: dict[str, Stop], stop_id: str) -> RouteStopOut:
    stop = stops[stop_id]
    return RouteStopOut(
        stop_id=stop_id,
        name=format_stop_display_name(stop),
        lat=stop.lat,
        lng=stop.lng,
    )


def _build_stop_sequence(connections: list[Connection], stops: dict[str, Stop]) -> list[RouteStopOut]:
    if not connections:
        return []
    sequence_ids = [connections[0].departure_stop]
    for connection in connections:
        sequence_ids.append(connection.arrival_stop)
    return [_to_route_stop(stops, stop_id) for stop_id in sequence_ids]


def _merge_transit_group(connections: list[Connection], stops: dict[str, Stop]) -> RouteLegOut:
    first = connections[0]
    last = connections[-1]
    from_lat, from_lng = _stop_coords(stops, first.departure_stop)
    to_lat, to_lng = _stop_coords(stops, last.arrival_stop)
    return RouteLegOut(
        type="transit",
        from_stop_id=first.departure_stop,
        to_stop_id=last.arrival_stop,
        from_name=_stop_label(stops, first.departure_stop),
        to_name=_stop_label(stops, last.arrival_stop),
        from_lat=from_lat,
        from_lng=from_lng,
        to_lat=to_lat,
        to_lng=to_lng,
        line=first.route_short_name,
        departure_ts=first.departure_ts,
        arrival_ts=last.arrival_ts,
        stops=_build_stop_sequence(connections, stops),
    )


def _reconstruct_legs(
    request: RouteRequest,
    stops: dict[str, Stop],
    journey_pointer: dict[str, _JourneyPointer],
    dest_stop_id: str,
    final_walk_seconds: int,
) -> list[RouteLegOut]:
    chain: list[_JourneyPointer] = []
    current = dest_stop_id
    visited: set[str] = set()
    while current in journey_pointer and current not in visited:
        visited.add(current)
        pointer = journey_pointer[current]
        chain.append(pointer)
        if isinstance(pointer, _WalkPointer):
            if pointer.origin.kind == "point":
                break
            if pointer.origin.stop_id is None:
                break
            current = pointer.origin.stop_id
        else:
            current = pointer.connection.departure_stop

    chain.reverse()

    legs: list[RouteLegOut] = []
    transit_group: list[Connection] = []

    def flush_transit() -> None:
        nonlocal transit_group
        if transit_group:
            legs.append(_merge_transit_group(transit_group, stops))
            transit_group = []

    for pointer in chain:
        if isinstance(pointer, _TransitPointer):
            conn = pointer.connection
            if transit_group and transit_group[-1].trip_id != conn.trip_id:
                flush_transit()
            transit_group.append(conn)
        else:
            flush_transit()
            legs.append(_build_walk_leg(pointer, stops))
    flush_transit()

    if final_walk_seconds > 0 and request.end_lat is not None and request.end_lng is not None:
        from_lat, from_lng = _stop_coords(stops, dest_stop_id)
        legs.append(
            RouteLegOut(
                type="walk",
                from_stop_id=dest_stop_id,
                to_stop_id=None,
                from_name=_stop_label(stops, dest_stop_id),
                to_name="Własny punkt",
                from_lat=from_lat,
                from_lng=from_lng,
                to_lat=request.end_lat,
                to_lng=request.end_lng,
                duration_seconds=final_walk_seconds,
            )
        )

    return legs


def find_route(
    request: RouteRequest,
    store: ConnectionStore,
    gtfs: GtfsData,
    footpaths: FootpathMap,
) -> RouteResponse:
    max_walk_seconds = request.max_walk_time_mins * 60
    stops = gtfs.stops
    earliest_arrival: dict[str, int] = {}
    journey_pointer: dict[str, _JourneyPointer] = {}

    origin, origin_edges = _origin_edges(request, footpaths, stops, max_walk_seconds)
    if not origin_edges:
        return RouteResponse(found=False)

    for stop_id, walk_seconds in origin_edges:
        arrival = request.departure_ts + walk_seconds
        if arrival < earliest_arrival.get(stop_id, INF):
            earliest_arrival[stop_id] = arrival
            if walk_seconds == 0 and origin.kind == "stop":
                continue
            journey_pointer[stop_id] = _WalkPointer(
                origin=origin,
                to_stop=stop_id,
                duration_seconds=walk_seconds,
            )

    for connection in _flatten_connections(store):
        dep_arrival = earliest_arrival.get(connection.departure_stop, INF)
        if dep_arrival >= INF or connection.departure_ts < dep_arrival:
            continue
        if connection.arrival_ts < earliest_arrival.get(connection.arrival_stop, INF):
            earliest_arrival[connection.arrival_stop] = connection.arrival_ts
            journey_pointer[connection.arrival_stop] = _TransitPointer(connection=connection)
            _relax_footpaths(
                connection.arrival_stop,
                connection.arrival_ts,
                footpaths,
                max_walk_seconds,
                earliest_arrival,
                journey_pointer,
            )

    destination = _resolve_destination(request, stops, max_walk_seconds, earliest_arrival)
    if destination is None:
        return RouteResponse(found=False)

    arrival_ts, dest_stop_id, final_walk_seconds = destination
    legs = _reconstruct_legs(request, stops, journey_pointer, dest_stop_id, final_walk_seconds)
    return RouteResponse(found=True, arrival_ts=arrival_ts, legs=legs)
