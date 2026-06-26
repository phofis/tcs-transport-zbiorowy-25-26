import L from "leaflet";
import { useCallback, useEffect, useState } from "react";
import { useMap, useMapEvents } from "react-leaflet";

import { useApp } from "@/context/AppContext";
import type { Stop } from "@/types/stop";
import StopMarker from "./StopMarker";

const MIN_STOP_ZOOM = 14;

function useStatusControl(
  map: L.Map,
  loadState: "loading" | "ready" | "error",
  errorMessage: string | null,
) {
  useEffect(() => {
    if (loadState === "ready") {
      return;
    }

    const StatusControl = L.Control.extend({
      onAdd: () => {
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
      },
    });
    const control = new StatusControl({ position: "topleft" });
    control.addTo(map);
    return () => {
      control.remove();
    };
  }, [map, loadState, errorMessage]);
}

export default function StopMarkersLayer() {
  const map = useMap();
  const { stops, stopsLoadState, stopsError } = useApp();
  const [visibleStops, setVisibleStops] = useState<Stop[]>([]);

  useStatusControl(map, stopsLoadState, stopsError);

  const updateVisibleStops = useCallback(() => {
    if (map.getZoom() < MIN_STOP_ZOOM) {
      setVisibleStops([]);
      return;
    }

    const bounds = map.getBounds();
    setVisibleStops(stops.filter((stop) => bounds.contains([stop.lat, stop.lng])));
  }, [stops, map]);

  useEffect(() => {
    updateVisibleStops();
  }, [stops, updateVisibleStops]);

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
