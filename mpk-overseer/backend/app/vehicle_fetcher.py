from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx
from google.transit import gtfs_realtime_pb2

from app.config import VEHICLE_POLL_INTERVAL, VEHICLE_POSITIONS_FEEDS
from app.gtfs_loader import GtfsData
from app.models import VehicleOut
from app import vehicle_cache

logger = logging.getLogger(__name__)


@dataclass
class FeedTracker:
    etag: str | None = None
    last_modified: str | None = None


def _resolve_line(gtfs: GtfsData, route_id: str, trip_id: str) -> tuple[str, str] | None:
    if route_id and route_id in gtfs.routes:
        return route_id, gtfs.routes[route_id].route_short_name

    if trip_id and trip_id in gtfs.trips:
        trip = gtfs.trips[trip_id]
        route = gtfs.routes.get(trip.route_id)
        if route is not None:
            return trip.route_id, route.route_short_name

    return None


def _parse_feed(content: bytes, gtfs: GtfsData) -> list[VehicleOut]:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)

    vehicles: list[VehicleOut] = []
    for entity in feed.entity:
        vehicle = entity.vehicle
        if not vehicle.HasField("position"):
            continue

        route_id = vehicle.trip.route_id if vehicle.HasField("trip") and vehicle.trip.route_id else ""
        trip_id = vehicle.trip.trip_id if vehicle.HasField("trip") and vehicle.trip.trip_id else ""

        resolved = _resolve_line(gtfs, route_id, trip_id)
        if resolved is None:
            continue
        route_id, line = resolved

        vehicle_id = vehicle.vehicle.id if vehicle.HasField("vehicle") and vehicle.vehicle.id else entity.id
        if not vehicle_id:
            continue

        bearing: float | None = None
        if vehicle.position.HasField("bearing"):
            bearing = vehicle.position.bearing

        timestamp = int(vehicle.timestamp) if vehicle.HasField("timestamp") else 0

        vehicles.append(
            VehicleOut(
                vehicle_id=vehicle_id,
                route_id=route_id,
                line=line,
                lat=vehicle.position.latitude,
                lng=vehicle.position.longitude,
                bearing=bearing,
                timestamp=timestamp,
            )
        )

    return vehicles


def _store_tracker(tracker: FeedTracker, response: httpx.Response) -> None:
    etag = response.headers.get("etag")
    last_modified = response.headers.get("last-modified")
    if etag:
        tracker.etag = etag
    if last_modified:
        tracker.last_modified = last_modified


async def _poll_feed(
    client: httpx.AsyncClient,
    feed_key: str,
    url: str,
    tracker: FeedTracker,
    gtfs: GtfsData,
) -> bool:
    headers: dict[str, str] = {}
    if tracker.etag:
        headers["If-None-Match"] = tracker.etag
    if tracker.last_modified:
        headers["If-Modified-Since"] = tracker.last_modified

    response = await client.get(url, headers=headers)
    if response.status_code == 304:
        return False

    response.raise_for_status()
    _store_tracker(tracker, response)

    vehicles = _parse_feed(response.content, gtfs)
    return vehicle_cache.update_feed(feed_key, vehicles, notify=False)


async def vehicle_fetch_loop(gtfs: GtfsData) -> None:
    trackers = {feed_key: FeedTracker() for feed_key in VEHICLE_POSITIONS_FEEDS}
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        while True:
            try:
                changed_any = False
                for feed_key, url in VEHICLE_POSITIONS_FEEDS.items():
                    try:
                        if await _poll_feed(client, feed_key, url, trackers[feed_key], gtfs):
                            changed_any = True
                    except Exception as exc:
                        logger.warning("Failed to poll %s (%s): %s", feed_key, url, exc)
                if changed_any:
                    vehicle_cache.notify_subscribers()
                    logger.debug("Vehicle cache updated")
            except Exception as exc:
                logger.warning("Vehicle fetch loop error: %s", exc)

            await asyncio.sleep(VEHICLE_POLL_INTERVAL)
