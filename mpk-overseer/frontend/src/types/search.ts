import type { Stop } from "@/types/stop";

export type Endpoint =
  | { kind: "stop"; stop: Stop }
  | { kind: "point"; lat: number; lng: number };

export type PickMode = "start" | "end" | null;

export type StopsLoadState = "loading" | "ready" | "error";
