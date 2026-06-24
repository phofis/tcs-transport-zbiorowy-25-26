import type { StopKind } from "./stop";

export interface Departure {
  departure_ts: number;
  trip_id: string;
  headsign?: string | null;
}

export interface LineDepartures {
  line: string;
  kind: StopKind;
  departures: Departure[];
}

export interface StopDepartures {
  stop_id: string;
  generated_ts: number;
  lines: LineDepartures[];
}
