from __future__ import annotations

import asyncio

from app.models import VehicleOut

_vehicles: dict[str, VehicleOut] = {}
_vehicle_feed: dict[str, str] = {}
_subscribers: list[asyncio.Queue[None]] = []


def subscribe() -> asyncio.Queue[None]:
    queue: asyncio.Queue[None] = asyncio.Queue(maxsize=1)
    _subscribers.append(queue)
    return queue


def unsubscribe(queue: asyncio.Queue[None]) -> None:
    if queue in _subscribers:
        _subscribers.remove(queue)


def _notify() -> None:
    for queue in list(_subscribers):
        try:
            queue.put_nowait(None)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            queue.put_nowait(None)


def _vehicle_position_changed(existing: VehicleOut, vehicle: VehicleOut) -> bool:
    return (
        existing.lat != vehicle.lat
        or existing.lng != vehicle.lng
        or existing.line != vehicle.line
        or existing.route_id != vehicle.route_id
    )


def update_feed(feed_key: str, vehicles: list[VehicleOut], *, notify: bool = True) -> bool:
    global _vehicles, _vehicle_feed

    old_from_feed = {vehicle_id for vehicle_id, source in _vehicle_feed.items() if source == feed_key}
    if not vehicles and old_from_feed:
        return False

    new_ids = {vehicle.vehicle_id for vehicle in vehicles}
    changed = bool(old_from_feed - new_ids)

    for vehicle_id in old_from_feed - new_ids:
        del _vehicles[vehicle_id]
        del _vehicle_feed[vehicle_id]

    for vehicle in vehicles:
        existing = _vehicles.get(vehicle.vehicle_id)
        if existing is None or _vehicle_position_changed(existing, vehicle):
            changed = True
        _vehicles[vehicle.vehicle_id] = vehicle
        _vehicle_feed[vehicle.vehicle_id] = feed_key

    if changed and notify:
        _notify()
    return changed


def notify_subscribers() -> None:
    _notify()


def snapshot() -> list[VehicleOut]:
    return list(_vehicles.values())
