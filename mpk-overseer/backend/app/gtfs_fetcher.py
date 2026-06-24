from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.config import GTFS_CACHE_DIR, GTFS_FEED_URLS

logger = logging.getLogger(__name__)


async def download_gtfs_feeds(cache_dir: Path | None = None) -> list[Path]:
    """Pobiera statyczne paczki GTFS z ZTP Kraków i zapisuje je w katalogu cache."""
    target_dir = cache_dir or Path(GTFS_CACHE_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        for url in GTFS_FEED_URLS:
            filename = url.rsplit("/", 1)[-1]
            dest = target_dir / filename
            logger.info("Downloading GTFS feed %s", url)
            response = await client.get(url)
            response.raise_for_status()
            dest.write_bytes(response.content)
            paths.append(dest)
            logger.info("Saved GTFS feed to %s (%d bytes)", dest, len(response.content))

    return paths


def list_cached_feeds(cache_dir: Path | None = None) -> list[Path]:
    target_dir = cache_dir or Path(GTFS_CACHE_DIR)
    if not target_dir.is_dir():
        return []
    return sorted(target_dir.glob("GTFS_KRK_*.zip"))


async def ensure_gtfs_feeds(cache_dir: Path | None = None) -> list[Path]:
    """Pobiera feedy z ZTP; przy błędzie sieci używa ostatniej wersji z cache."""
    target_dir = cache_dir or Path(GTFS_CACHE_DIR)
    try:
        return await download_gtfs_feeds(target_dir)
    except Exception as exc:
        cached = list_cached_feeds(target_dir)
        if cached:
            logger.warning(
                "GTFS download failed (%s), using cached feeds: %s",
                exc,
                ", ".join(path.name for path in cached),
            )
            return cached
        raise RuntimeError(
            "Failed to download GTFS feeds from ZTP and no cached copies are available."
        ) from exc
