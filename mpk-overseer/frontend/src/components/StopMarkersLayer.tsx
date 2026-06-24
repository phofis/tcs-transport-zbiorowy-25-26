import L from "leaflet";
import { useCallback, useEffect, useState } from "react";
import { useMap, useMapEvents } from "react-leaflet";

import { fetchStopsWithRetry } from "../lib/api";
import type { Stop } from "../types/stop";
import StopMarker from "./StopMarker";

const MIN_STOP_ZOOM = 14;

type LoadState = "loading" | "ready" | "error";

function useStatusControl(
  map: L.Map,
  loadState: LoadState,
  errorMessage: string | null,
) {
  useEffect(() => {
    if (loadState === "ready") {
      return;
    }

    const control = L.control({ position: "topleft" });
    control.onAdd = () => {
      const div = L.DomUtil.create("div");
      div.style.cssText =
        "padding: 6px 12px; font-size: 14px; border-radius: 4px; " +
        "background: rgba(255,255,255,0.92); box-shadow: 0 1px 4px rgba(0,0,0,0.2);";
      if (loadState === "error") {
        div.style.color = "#b91c1c";
        div.style.background = "#fef2f2";
        div.textContent = errorMessage ?? "Backend niedostępny";
      } else {
        div.textContent = "Ładowanie przystanków…";
      }
      return div;
    };
    control.addTo(map);
    return () => {
      control.remove();
    };
  }, [map, loadState, errorMessage]);
}

export default function StopMarkersLayer() {
  const map = useMap();
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [allStops, setAllStops] = useState<Stop[]>([]);
  const [visibleStops, setVisibleStops] = useState<Stop[]>([]);

  useStatusControl(map, loadState, errorMessage);

  const updateVisibleStops = useCallback(() => {
    if (map.getZoom() < MIN_STOP_ZOOM) {
      setVisibleStops([]);
      return;
    }

    const bounds = map.getBounds();
    setVisibleStops(
      allStops.filter((stop) => bounds.contains([stop.lat, stop.lng])),
    );
  }, [allStops, map]);

  useEffect(() => {
    let cancelled = false;

    fetchStopsWithRetry()
      .then((stops) => {
        if (!cancelled) {
          setAllStops(stops);
          setLoadState("ready");
          setErrorMessage(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setLoadState("error");
          setErrorMessage(
            error instanceof Error ? error.message : "Nie udało się załadować przystanków",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    updateVisibleStops();
  }, [allStops, updateVisibleStops]);

  useMapEvents({
    moveend: updateVisibleStops,
    zoomend: updateVisibleStops,
  });

  return (
    <>
      {visibleStops.map((stop) => (
        <StopMarker key={stop.stop_id} stop={stop} />
      ))}
    </>
  );
}
