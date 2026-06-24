import os

CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
GTFS_BASE_URL: str = os.getenv("GTFS_BASE_URL", "https://gtfs.ztp.krakow.pl")
GTFS_CACHE_DIR: str = os.getenv("GTFS_CACHE_DIR", "/app/data/gtfs")
GTFS_FEED_URLS: list[str] = [
    f"{GTFS_BASE_URL}/GTFS_KRK_A.zip",
    f"{GTFS_BASE_URL}/GTFS_KRK_T.zip",
    f"{GTFS_BASE_URL}/GTFS_KRK_M.zip",
]
