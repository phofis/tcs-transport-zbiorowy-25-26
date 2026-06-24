import type { StopDepartures } from "../types/departure";
import type { Stop } from "../types/stop";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface HealthResponse {
  status: string;
  gtfs_ready: boolean;
  stops_count?: number;
}

const RETRY_INTERVAL_MS = 2000;
const MAX_RETRIES = 30;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/health`);
  const data = (await res.json()) as HealthResponse;
  if (!res.ok) {
    return { ...data, gtfs_ready: false };
  }
  return data;
}

export async function fetchStops(): Promise<Stop[]> {
  const res = await fetch(`${API_URL}/api/stops`);
  if (!res.ok) {
    throw new Error(`Failed to fetch stops: ${res.status}`);
  }
  return res.json();
}

export async function fetchStopsWithRetry(): Promise<Stop[]> {
  for (let attempt = 0; attempt < MAX_RETRIES; attempt += 1) {
    try {
      const health = await fetchHealth();
      if (health.gtfs_ready) {
        return await fetchStops();
      }
    } catch {
      // Backend not reachable yet — retry.
    }
    await sleep(RETRY_INTERVAL_MS);
  }
  throw new Error("Backend niedostępny lub GTFS nie załadowane");
}

export async function fetchStopDepartures(stopId: string): Promise<StopDepartures> {
  const res = await fetch(`${API_URL}/api/stops/${encodeURIComponent(stopId)}/departures`);
  if (!res.ok) {
    throw new Error(`Failed to fetch departures: ${res.status}`);
  }
  return res.json();
}
