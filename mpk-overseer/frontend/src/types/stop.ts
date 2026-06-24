export type StopKind = "tram" | "bus" | "mixed";

export interface Stop {
  stop_id: string;
  name: string;
  lat: number;
  lng: number;
  kind: StopKind;
  platform?: string | null;
}
