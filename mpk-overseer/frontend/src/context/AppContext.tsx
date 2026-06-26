import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { fetchRoute, fetchStopsWithRetry } from "@/lib/api";
import { defaultDepartureTime, warsawDateTimeToEpoch } from "@/lib/departureTime";
import type { RouteRequest, RouteResponse } from "@/types/route";
import type { Endpoint, PickMode, StopsLoadState } from "@/types/search";
import type { Stop } from "@/types/stop";

interface AppContextValue {
  stops: Stop[];
  stopsLoadState: StopsLoadState;
  stopsError: string | null;
  startEndpoint: Endpoint | null;
  endEndpoint: Endpoint | null;
  pickMode: PickMode;
  maxWalkMins: number;
  departureDate: Date;
  departureTime: string;
  route: RouteResponse | null;
  routeLoading: boolean;
  routeError: string | null;
  setStartEndpoint: (endpoint: Endpoint | null) => void;
  setEndEndpoint: (endpoint: Endpoint | null) => void;
  setPickMode: (mode: PickMode) => void;
  setMaxWalkMins: (mins: number) => void;
  setDepartureDate: (date: Date) => void;
  setDepartureTime: (time: string) => void;
  setEndpointFromMap: (mode: "start" | "end", lat: number, lng: number) => void;
  searchRoute: () => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

function endpointToRouteFields(
  endpoint: Endpoint | null,
  prefix: "start" | "end",
): Partial<RouteRequest> {
  if (!endpoint) {
    return {};
  }
  if (endpoint.kind === "stop") {
    return prefix === "start"
      ? { start_stop_id: endpoint.stop.stop_id }
      : { end_stop_id: endpoint.stop.stop_id };
  }
  return prefix === "start"
    ? { start_lat: endpoint.lat, start_lng: endpoint.lng }
    : { end_lat: endpoint.lat, end_lng: endpoint.lng };
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [stops, setStops] = useState<Stop[]>([]);
  const [stopsLoadState, setStopsLoadState] = useState<StopsLoadState>("loading");
  const [stopsError, setStopsError] = useState<string | null>(null);
  const [startEndpoint, setStartEndpoint] = useState<Endpoint | null>(null);
  const [endEndpoint, setEndEndpoint] = useState<Endpoint | null>(null);
  const [pickMode, setPickMode] = useState<PickMode>(null);
  const [maxWalkMins, setMaxWalkMins] = useState(5);
  const [departureDate, setDepartureDate] = useState(() => new Date());
  const [departureTime, setDepartureTime] = useState(defaultDepartureTime);
  const [route, setRoute] = useState<RouteResponse | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchStopsWithRetry()
      .then((loaded) => {
        if (!cancelled) {
          setStops(loaded);
          setStopsLoadState("ready");
          setStopsError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setStopsLoadState("error");
          setStopsError(error instanceof Error ? error.message : "Nie udało się załadować przystanków");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const setEndpointFromMap = useCallback((mode: "start" | "end", lat: number, lng: number) => {
    const endpoint: Endpoint = { kind: "point", lat, lng };
    if (mode === "start") {
      setStartEndpoint(endpoint);
    } else {
      setEndEndpoint(endpoint);
    }
    setPickMode(null);
  }, []);

  const searchRoute = useCallback(async () => {
    if (!startEndpoint || !endEndpoint) {
      setRouteError("Wybierz punkt startowy i docelowy");
      return;
    }
    setRouteLoading(true);
    setRouteError(null);
    try {
      const request: RouteRequest = {
        departure_ts: warsawDateTimeToEpoch(departureDate, departureTime),
        max_walk_time_mins: maxWalkMins,
        ...endpointToRouteFields(startEndpoint, "start"),
        ...endpointToRouteFields(endEndpoint, "end"),
      };
      const result = await fetchRoute(request);
      setRoute(result);
      if (!result.found) {
        setRouteError("Nie znaleziono połączenia");
      }
    } catch (error: unknown) {
      setRoute(null);
      setRouteError(error instanceof Error ? error.message : "Błąd wyszukiwania trasy");
    } finally {
      setRouteLoading(false);
    }
  }, [startEndpoint, endEndpoint, departureDate, departureTime, maxWalkMins]);

  const value = useMemo(
    () => ({
      stops,
      stopsLoadState,
      stopsError,
      startEndpoint,
      endEndpoint,
      pickMode,
      maxWalkMins,
      departureDate,
      departureTime,
      route,
      routeLoading,
      routeError,
      setStartEndpoint,
      setEndEndpoint,
      setPickMode,
      setMaxWalkMins,
      setDepartureDate,
      setDepartureTime,
      setEndpointFromMap,
      searchRoute,
    }),
    [
      stops,
      stopsLoadState,
      stopsError,
      startEndpoint,
      endEndpoint,
      pickMode,
      maxWalkMins,
      departureDate,
      departureTime,
      route,
      routeLoading,
      routeError,
      setEndpointFromMap,
      searchRoute,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within AppProvider");
  }
  return context;
}
