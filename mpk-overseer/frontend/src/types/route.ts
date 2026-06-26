export interface RouteStop {
  stop_id: string;
  name: string;
  lat: number;
  lng: number;
}

export interface RouteLeg {
  type: "walk" | "transit";
  from_stop_id?: string | null;
  to_stop_id?: string | null;
  from_name?: string | null;
  to_name?: string | null;
  from_lat?: number | null;
  from_lng?: number | null;
  to_lat?: number | null;
  to_lng?: number | null;
  line?: string | null;
  departure_ts?: number | null;
  arrival_ts?: number | null;
  duration_seconds?: number | null;
  stops?: RouteStop[];
}

export interface RouteResponse {
  found: boolean;
  arrival_ts?: number | null;
  legs: RouteLeg[];
}

export interface RouteRequest {
  start_stop_id?: string;
  start_lat?: number;
  start_lng?: number;
  end_stop_id?: string;
  end_lat?: number;
  end_lng?: number;
  departure_ts: number;
  max_walk_time_mins: number;
}
