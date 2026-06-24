from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app import vehicle_cache

logger = logging.getLogger(__name__)


def _filter_vehicles(line_filter: set[str]):
    vehicles = vehicle_cache.snapshot()
    if not line_filter:
        return vehicles
    return [vehicle for vehicle in vehicles if vehicle.line in line_filter]


async def vehicles_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    line_filter: set[str] = set()
    update_queue = vehicle_cache.subscribe()

    async def receive_loop() -> None:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict) and "filter" in message:
                filter_value = message["filter"]
                if isinstance(filter_value, list):
                    line_filter.clear()
                    line_filter.update(str(line) for line in filter_value)
                    try:
                        update_queue.put_nowait(None)
                    except asyncio.QueueFull:
                        pass

    async def push_loop() -> None:
        while True:
            payload = {
                "type": "vehicles",
                "data": [vehicle.model_dump() for vehicle in _filter_vehicles(line_filter)],
            }
            await websocket.send_json(payload)
            await update_queue.get()

    receive_task = asyncio.create_task(receive_loop())
    push_task = asyncio.create_task(push_loop())

    try:
        done, pending = await asyncio.wait(
            {receive_task, push_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            task.result()
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
    finally:
        vehicle_cache.unsubscribe(update_queue)
        receive_task.cancel()
        push_task.cancel()
        try:
            await receive_task
        except (asyncio.CancelledError, WebSocketDisconnect):
            pass
        try:
            await push_task
        except asyncio.CancelledError:
            pass
