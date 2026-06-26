import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.blocks import GRACE, HORIZON, REGEN_INTERVAL, ConnectionStore, build_initial_store, regenerate_store
from app.config import CORS_ORIGINS
from app.csa import find_route
from app.departures import get_stop_departures
from app.footpaths import FootpathMap, load_footpaths
from app.gtfs_fetcher import ensure_gtfs_feeds
from app.gtfs_loader import GtfsData, load_gtfs
from app.models import RouteRequest, RouteResponse, StopDeparturesOut, StopOut
from app.vehicle_fetcher import vehicle_fetch_loop
from app.websocket_vehicles import vehicles_websocket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

gtfs_data: GtfsData | None = None
connection_store: ConnectionStore | None = None
footpaths_data: FootpathMap | None = None


async def _regen_loop() -> None:
    while True:
        await asyncio.sleep(REGEN_INTERVAL)
        if gtfs_data is None or connection_store is None:
            continue
        await asyncio.to_thread(regenerate_store, connection_store, gtfs_data)
        logger.info("Regenerated connection blocks")


@asynccontextmanager
async def lifespan(_: FastAPI):
    global gtfs_data, connection_store, footpaths_data
    feed_paths = await ensure_gtfs_feeds()
    gtfs_data = await asyncio.to_thread(
        load_gtfs,
        [str(path) for path in feed_paths],
    )
    logger.info("Loaded %d stops from GTFS", len(gtfs_data.stops))

    footpaths_data = await asyncio.to_thread(load_footpaths)

    connection_store = await asyncio.to_thread(build_initial_store, gtfs_data)
    block_count = len(connection_store.snapshot())
    connection_count = sum(len(block.connections) for block in connection_store.snapshot())
    logger.info(
        "Built connection store: %d blocks, %d connections",
        block_count,
        connection_count,
    )

    regen_task = asyncio.create_task(_regen_loop())
    vehicle_task = asyncio.create_task(vehicle_fetch_loop(gtfs_data))
    yield
    vehicle_task.cancel()
    regen_task.cancel()
    try:
        await vehicle_task
    except asyncio.CancelledError:
        pass
    try:
        await regen_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="mpk-overseer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    if gtfs_data is None or connection_store is None:
        return JSONResponse(
            status_code=503,
            content={"status": "loading", "gtfs_ready": False},
        )
    return {
        "status": "ok",
        "gtfs_ready": True,
        "stops_count": len(gtfs_data.stops),
    }


@app.get("/api/stops", response_model=list[StopOut])
def list_stops() -> list[StopOut]:
    assert gtfs_data is not None
    return sorted(
        (
            StopOut(
                stop_id=stop.stop_id,
                name=stop.name,
                lat=stop.lat,
                lng=stop.lng,
                kind=gtfs_data.stop_kind[stop.stop_id],
                platform=stop.platform,
            )
            for stop in gtfs_data.stops.values()
        ),
        key=lambda stop: stop.name,
    )


@app.get("/api/stops/{stop_id}/departures", response_model=StopDeparturesOut)
def stop_departures(stop_id: str) -> StopDeparturesOut:
    assert gtfs_data is not None
    assert connection_store is not None
    if stop_id not in gtfs_data.stops:
        raise HTTPException(status_code=404, detail=f"Stop {stop_id} not found")
    return get_stop_departures(connection_store, gtfs_data, stop_id)


@app.post("/api/route", response_model=RouteResponse)
def route_search(request: RouteRequest) -> RouteResponse:
    assert gtfs_data is not None
    assert connection_store is not None
    assert footpaths_data is not None

    now = int(time.time())
    if request.departure_ts < now - GRACE or request.departure_ts > now + HORIZON:
        raise HTTPException(
            status_code=400,
            detail=(
                f"departure_ts must be within the connection window "
                f"[{now - GRACE}, {now + HORIZON}]"
            ),
        )

    if request.start_stop_id is not None and request.start_stop_id not in gtfs_data.stops:
        raise HTTPException(status_code=400, detail=f"Start stop {request.start_stop_id} not found")
    if request.end_stop_id is not None and request.end_stop_id not in gtfs_data.stops:
        raise HTTPException(status_code=400, detail=f"End stop {request.end_stop_id} not found")

    return find_route(request, connection_store, gtfs_data, footpaths_data)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await vehicles_websocket(websocket)
