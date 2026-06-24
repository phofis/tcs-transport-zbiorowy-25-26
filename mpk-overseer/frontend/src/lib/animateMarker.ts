import type L from "leaflet";

export type LatLng = [number, number];

const MIN_MOVE_METERS = 4;
const MAX_ANIMATE_METERS = 1500;
export const MIN_ANIMATION_MS = 1500;
export const MAX_ANIMATION_MS = 1000;
export const DEFAULT_ANIMATION_MS = 1500;

function haversineMeters(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return 6_371_000 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function animationDurationFromGap(gapMs: number): number {
  if (!Number.isFinite(gapMs) || gapMs <= 0) {
    return DEFAULT_ANIMATION_MS;
  }
  return Math.min(MAX_ANIMATION_MS, Math.max(MIN_ANIMATION_MS, gapMs));
}

export function predictAnimationDurationMs(
  previousTimestamp: number,
  previousUpdateMs: number,
  nextTimestamp: number,
  nowMs: number,
): number {
  if (previousTimestamp > 0 && nextTimestamp > previousTimestamp) {
    return animationDurationFromGap((nextTimestamp - previousTimestamp) * 1000);
  }
  if (previousUpdateMs > 0) {
    return animationDurationFromGap(nowMs - previousUpdateMs);
  }
  return DEFAULT_ANIMATION_MS;
}

export function animateMarker(
  markerInstance: L.Marker,
  start: LatLng,
  end: LatLng,
  duration = DEFAULT_ANIMATION_MS,
): () => void {
  const distance = haversineMeters(start[0], start[1], end[0], end[1]);

  if (distance < MIN_MOVE_METERS) {
    return () => {};
  }

  if (distance > MAX_ANIMATE_METERS) {
    markerInstance.setLatLng(end);
    return () => {};
  }

  const startTime = performance.now();
  let frameId = 0;

  const update = (currentTime: number) => {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const lat = start[0] + (end[0] - start[0]) * progress;
    const lng = start[1] + (end[1] - start[1]) * progress;
    markerInstance.setLatLng([lat, lng]);
    if (progress < 1) {
      frameId = requestAnimationFrame(update);
    }
  };

  frameId = requestAnimationFrame(update);

  return () => {
    cancelAnimationFrame(frameId);
  };
}

export function markerLatLng(marker: L.Marker): LatLng {
  const { lat, lng } = marker.getLatLng();
  return [lat, lng];
}
