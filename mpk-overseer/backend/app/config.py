import os

CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
GTFS_BASE_URL: str = os.getenv("GTFS_BASE_URL", "https://gtfs.ztp.krakow.pl")
GTFS_CACHE_DIR: str = os.getenv("GTFS_CACHE_DIR", "/app/data/gtfs")
GTFS_FEED_URLS: list[str] = [
    f"{GTFS_BASE_URL}/GTFS_KRK_A.zip",
    f"{GTFS_BASE_URL}/GTFS_KRK_T.zip",
    f"{GTFS_BASE_URL}/GTFS_KRK_M.zip",
]
VEHICLE_POSITIONS_FEEDS: dict[str, str] = {
    "A": f"{GTFS_BASE_URL}/VehiclePositions_A.pb",
    "T": f"{GTFS_BASE_URL}/VehiclePositions_T.pb",
    "M": f"{GTFS_BASE_URL}/VehiclePositions_M.pb",
}
VEHICLE_POLL_INTERVAL: float = 1.0
