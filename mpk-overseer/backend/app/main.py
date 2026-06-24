import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.blocks import REGEN_INTERVAL, ConnectionStore, build_initial_store, regenerate_store
from app.config import CORS_ORIGINS
from app.departures import get_stop_departures
from app.gtfs_fetcher import ensure_gtfs_feeds
from app.gtfs_loader import GtfsData, load_gtfs
from app.models import StopDeparturesOut, StopOut

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

gtfs_data: GtfsData | None = None
connection_store: ConnectionStore | None = None


async def _regen_loop() -> None:
    while True:
        await asyncio.sleep(REGEN_INTERVAL)
        if gtfs_data is None or connection_store is None:
            continue
        await asyncio.to_thread(regenerate_store, connection_store, gtfs_data)
        logger.info("Regenerated connection blocks")


@asynccontextmanager
async def lifespan(_: FastAPI):
    global gtfs_data, connection_store
    feed_paths = await ensure_gtfs_feeds()
    gtfs_data = await asyncio.to_thread(
        load_gtfs,
        [str(path) for path in feed_paths],
    )
    logger.info("Loaded %d stops from GTFS", len(gtfs_data.stops))

    connection_store = await asyncio.to_thread(build_initial_store, gtfs_data)
    block_count = len(connection_store.snapshot())
    connection_count = sum(len(block.connections) for block in connection_store.snapshot())
    logger.info(
        "Built connection store: %d blocks, %d connections",
        block_count,
        connection_count,
    )

    regen_task = asyncio.create_task(_regen_loop())
    yield
    regen_task.cancel()
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
