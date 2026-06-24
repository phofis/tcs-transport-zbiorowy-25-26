from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.gtfs_time import GTFS_WEEKDAY_FIELDS
from app.models import RouteInfo, Stop, StopKind, StopTime, TripInfo


@dataclass
class GtfsData:
    stops: dict[str, Stop]
    stop_kind: dict[str, StopKind]
    routes: dict[str, RouteInfo]
    trips: dict[str, TripInfo]
    stop_times_by_trip: dict[str, list[StopTime]]
    service_dates: dict[str, set[date]]


def _read_csv_rows(zip_file: zipfile.ZipFile, filename: str) -> list[dict[str, str]]:
    with zip_file.open(filename) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        return list(csv.DictReader(text))


def _format_platform(stop_desc: str | None, stop_code: str | None) -> str | None:
    if stop_desc and stop_desc.strip():
        desc = stop_desc.strip()
        if desc.isdigit():
            return str(int(desc))
        return desc
    if stop_code and "-" in stop_code:
        suffix = stop_code.rsplit("-", 1)[-1]
        if suffix.isdigit():
            return str(int(suffix))
    return None


def _load_stops(zip_file: zipfile.ZipFile) -> dict[str, Stop]:
    stops: dict[str, Stop] = {}
    for row in _read_csv_rows(zip_file, "stops.txt"):
        stop_id = row["stop_id"]
        stops[stop_id] = Stop(
            stop_id=stop_id,
            name=row["stop_name"],
            lat=float(row["stop_lat"]),
            lng=float(row["stop_lon"]),
            platform=_format_platform(
                row.get("stop_desc"),
                row.get("stop_code"),
            ),
        )
    return stops


def _load_routes(zip_file: zipfile.ZipFile) -> dict[str, RouteInfo]:
    routes: dict[str, RouteInfo] = {}
    for row in _read_csv_rows(zip_file, "routes.txt"):
        routes[row["route_id"]] = RouteInfo(
            route_short_name=row["route_short_name"],
            route_type=int(row["route_type"]),
        )
    return routes


def _load_trips(zip_file: zipfile.ZipFile) -> dict[str, TripInfo]:
    trips: dict[str, TripInfo] = {}
    for row in _read_csv_rows(zip_file, "trips.txt"):
        headsign = row.get("trip_headsign") or None
        trips[row["trip_id"]] = TripInfo(
            route_id=row["route_id"],
            service_id=row["service_id"],
            trip_headsign=headsign if headsign else None,
        )
    return trips


def _load_stop_times_by_trip(zip_file: zipfile.ZipFile) -> dict[str, list[StopTime]]:
    by_trip: dict[str, list[StopTime]] = defaultdict(list)
    for row in _read_csv_rows(zip_file, "stop_times.txt"):
        arrival = row.get("arrival_time") or None
        departure = row.get("departure_time") or None
        by_trip[row["trip_id"]].append(
            StopTime(
                stop_id=row["stop_id"],
                arrival_time=arrival if arrival else None,
                departure_time=departure if departure else None,
                stop_sequence=int(row["stop_sequence"]),
            )
        )
    return {
        trip_id: sorted(times, key=lambda stop_time: stop_time.stop_sequence)
        for trip_id, times in by_trip.items()
    }


def _parse_gtfs_date(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def _load_service_dates(zip_file: zipfile.ZipFile) -> dict[str, set[date]]:
    service_dates: dict[str, set[date]] = {}

    if "calendar.txt" in zip_file.namelist():
        for row in _read_csv_rows(zip_file, "calendar.txt"):
            service_id = row["service_id"]
            start = _parse_gtfs_date(row["start_date"])
            end = _parse_gtfs_date(row["end_date"])
            active_days = [int(row[field]) for field in GTFS_WEEKDAY_FIELDS]
            dates: set[date] = set()
            current = start
            while current <= end:
                if active_days[current.weekday()]:
                    dates.add(current)
                current += timedelta(days=1)
            service_dates[service_id] = dates

    if "calendar_dates.txt" in zip_file.namelist():
        for row in _read_csv_rows(zip_file, "calendar_dates.txt"):
            service_id = row["service_id"]
            service_date = _parse_gtfs_date(row["date"])
            exception_type = int(row["exception_type"])
            if exception_type == 1:
                service_dates.setdefault(service_id, set()).add(service_date)
            elif exception_type == 2:
                service_dates.get(service_id, set()).discard(service_date)

    return service_dates


def _load_stop_kind(
    stop_times_by_trip: dict[str, list[StopTime]],
    trips: dict[str, TripInfo],
    routes: dict[str, RouteInfo],
) -> dict[str, StopKind]:
    stop_route_types: dict[str, set[int]] = defaultdict(set)
    for trip_id, stop_times in stop_times_by_trip.items():
        trip = trips.get(trip_id)
        if trip is None:
            continue
        route = routes.get(trip.route_id)
        if route is None:
            continue
        for stop_time in stop_times:
            stop_route_types[stop_time.stop_id].add(route.route_type)
    return {
        stop_id: _compute_stop_kind(route_types)
        for stop_id, route_types in stop_route_types.items()
    }


def _compute_stop_kind(route_types: set[int]) -> StopKind:
    has_tram = 0 in route_types
    has_bus = 3 in route_types
    if has_tram and has_bus:
        return "mixed"
    if has_tram:
        return "tram"
    if has_bus:
        return "bus"
    return "mixed"


def _merge_service_dates(
    target: dict[str, set[date]],
    source: dict[str, set[date]],
) -> None:
    for service_id, dates in source.items():
        target.setdefault(service_id, set()).update(dates)


def _load_gtfs_zip(path: str) -> tuple[
    dict[str, Stop],
    dict[str, RouteInfo],
    dict[str, TripInfo],
    dict[str, list[StopTime]],
    dict[str, set[date]],
]:
    with zipfile.ZipFile(path, "r") as zip_file:
        routes = _load_routes(zip_file)
        trips = _load_trips(zip_file)
        stop_times_by_trip = _load_stop_times_by_trip(zip_file)
        return (
            _load_stops(zip_file),
            routes,
            trips,
            stop_times_by_trip,
            _load_service_dates(zip_file),
        )


def load_gtfs(paths: str | list[str]) -> GtfsData:
    if isinstance(paths, str):
        paths = [paths]

    stops: dict[str, Stop] = {}
    routes: dict[str, RouteInfo] = {}
    trips: dict[str, TripInfo] = {}
    stop_times_by_trip: dict[str, list[StopTime]] = {}
    service_dates: dict[str, set[date]] = {}

    for path in paths:
        zip_stops, zip_routes, zip_trips, zip_stop_times, zip_service_dates = _load_gtfs_zip(
            path
        )
        stops.update(zip_stops)
        routes.update(zip_routes)
        trips.update(zip_trips)
        for trip_id, times in zip_stop_times.items():
            stop_times_by_trip[trip_id] = times
        _merge_service_dates(service_dates, zip_service_dates)

    stop_kind_from_times = _load_stop_kind(stop_times_by_trip, trips, routes)
    stop_kind = {
        stop_id: stop_kind_from_times.get(stop_id, "mixed") for stop_id in stops
    }

    return GtfsData(
        stops=stops,
        stop_kind=stop_kind,
        routes=routes,
        trips=trips,
        stop_times_by_trip=stop_times_by_trip,
        service_dates=service_dates,
    )
