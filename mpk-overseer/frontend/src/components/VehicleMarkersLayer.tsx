import L from "leaflet";
import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";

import { animateMarker, markerLatLng, predictAnimationDurationMs } from "../lib/animateMarker";
import { getVehicleIcon } from "../lib/vehicleIcon";
import type { Vehicle } from "../types/vehicle";
import { useVehicleSocket } from "../hooks/useVehicleSocket";

type MarkerEntry = {
  marker: L.Marker;
  line: string;
  cancelAnimation: (() => void) | null;
  lastTimestamp: number;
  lastPositionUpdateMs: number;
};

function useVehicleStatusControl(
  map: L.Map,
  connected: boolean,
  vehicleCount: number,
) {
  useEffect(() => {
    const StatusControl = L.Control.extend({
      onAdd: () => {
        const div = L.DomUtil.create("div");
        div.style.cssText =
          "padding: 6px 12px; font-size: 14px; border-radius: 4px; " +
          "background: rgba(255,255,255,0.92); box-shadow: 0 1px 4px rgba(0,0,0,0.2);";
        if (!connected) {
          div.textContent = "Łączenie z pojazdami…";
        } else {
          div.textContent = `${vehicleCount} pojazdów`;
        }
        return div;
      },
    });
    const control = new StatusControl({ position: "topright" });
    control.addTo(map);
    return () => {
      control.remove();
    };
  }, [map, connected, vehicleCount]);
}

function syncVehicleMarkers(map: L.Map, markers: Map<string, MarkerEntry>, vehicles: Vehicle[]) {
  const nowMs = performance.now();
  const incoming = new Map(vehicles.map((vehicle) => [vehicle.vehicle_id, vehicle]));

  for (const [vehicleId, entry] of markers) {
    if (!incoming.has(vehicleId)) {
      entry.cancelAnimation?.();
      entry.marker.remove();
      markers.delete(vehicleId);
    }
  }

  for (const vehicle of vehicles) {
    const nextPosition: L.LatLngExpression = [vehicle.lat, vehicle.lng];
    const existing = markers.get(vehicle.vehicle_id);

    if (!existing) {
      const marker = L.marker(nextPosition, {
        icon: getVehicleIcon(vehicle.line),
        zIndexOffset: 100,
      });
      marker.bindPopup(`Linia ${vehicle.line}`);
      marker.addTo(map);
      markers.set(vehicle.vehicle_id, {
        marker,
        line: vehicle.line,
        cancelAnimation: null,
        lastTimestamp: vehicle.timestamp,
        lastPositionUpdateMs: nowMs,
      });
      continue;
    }

    if (existing.line !== vehicle.line) {
      existing.marker.setIcon(getVehicleIcon(vehicle.line));
      existing.line = vehicle.line;
      existing.marker.setPopupContent(`Linia ${vehicle.line}`);
    }

    const current = markerLatLng(existing.marker);
    if (current[0] === vehicle.lat && current[1] === vehicle.lng) {
      continue;
    }

    const durationMs = predictAnimationDurationMs(
      existing.lastTimestamp,
      existing.lastPositionUpdateMs,
      vehicle.timestamp,
      nowMs,
    );

    existing.cancelAnimation?.();
    existing.cancelAnimation = animateMarker(
      existing.marker,
      current,
      [vehicle.lat, vehicle.lng],
      durationMs,
    );
    existing.lastTimestamp = vehicle.timestamp;
    existing.lastPositionUpdateMs = nowMs;
  }
}

export default function VehicleMarkersLayer() {
  const map = useMap();
  const { vehicles, connected } = useVehicleSocket([]);
  const markersRef = useRef<Map<string, MarkerEntry>>(new Map());

  useVehicleStatusControl(map, connected, vehicles.length);

  useEffect(() => {
    syncVehicleMarkers(map, markersRef.current, vehicles);
  }, [map, vehicles]);

  useEffect(
    () => () => {
      for (const entry of markersRef.current.values()) {
        entry.cancelAnimation?.();
        entry.marker.remove();
      }
      markersRef.current.clear();
    },
    [],
  );

  return null;
}
