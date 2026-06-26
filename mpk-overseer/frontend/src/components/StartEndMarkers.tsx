import L from "leaflet";
import { Fragment, useEffect } from "react";
import { CircleMarker, Marker, Polyline, useMap, useMapEvents } from "react-leaflet";

import { useApp } from "@/context/AppContext";
import type { RouteLeg } from "@/types/route";
import type { Endpoint } from "@/types/search";

function endpointCoords(endpoint: Endpoint): [number, number] {
  if (endpoint.kind === "stop") {
    return [endpoint.stop.lat, endpoint.stop.lng];
  }
  return [endpoint.lat, endpoint.lng];
}

const startIcon = L.divIcon({
  className: "",
  html: `<div style="width:18px;height:18px;border-radius:50%;background:#16a34a;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.35)"></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

const endIcon = L.divIcon({
  className: "",
  html: `<div style="width:18px;height:18px;border-radius:50%;background:#dc2626;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.35)"></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

const TRANSIT_COLOR = "#2563eb";
const INTERMEDIATE_COLOR = "#9ca3af";

function legPositions(leg: RouteLeg): [number, number][] {
  if (leg.stops && leg.stops.length >= 2) {
    return leg.stops.map((stop) => [stop.lat, stop.lng]);
  }
  if (
    leg.from_lat != null &&
    leg.from_lng != null &&
    leg.to_lat != null &&
    leg.to_lng != null
  ) {
    return [
      [leg.from_lat, leg.from_lng],
      [leg.to_lat, leg.to_lng],
    ];
  }
  return [];
}

export function MapPickHandler() {
  const { pickMode, setEndpointFromMap } = useApp();

  useMapEvents({
    click(event) {
      if (!pickMode) {
        return;
      }
      setEndpointFromMap(pickMode, event.latlng.lat, event.latlng.lng);
    },
  });

  return null;
}

export default function StartEndMarkers() {
  const { startEndpoint, endEndpoint, setStartEndpoint, setEndEndpoint } = useApp();

  return (
    <>
      {startEndpoint && (
        <Marker
          position={endpointCoords(startEndpoint)}
          icon={startIcon}
          draggable
          eventHandlers={{
            dragend: (event) => {
              const { lat, lng } = event.target.getLatLng();
              setStartEndpoint({ kind: "point", lat, lng });
            },
          }}
        />
      )}
      {endEndpoint && (
        <Marker
          position={endpointCoords(endEndpoint)}
          icon={endIcon}
          draggable
          eventHandlers={{
            dragend: (event) => {
              const { lat, lng } = event.target.getLatLng();
              setEndEndpoint({ kind: "point", lat, lng });
            },
          }}
        />
      )}
    </>
  );
}

function RouteFitBounds() {
  const map = useMap();
  const { route } = useApp();

  useEffect(() => {
    if (!route?.found) {
      return;
    }
    const points: [number, number][] = [];
    for (const leg of route.legs) {
      for (const position of legPositions(leg)) {
        points.push(position);
      }
    }
    if (points.length === 0) {
      return;
    }
    map.fitBounds(L.latLngBounds(points), { padding: [48, 48] });
  }, [map, route]);

  return null;
}

export function RouteLayer() {
  const { route } = useApp();
  if (!route?.found) {
    return null;
  }

  return (
    <>
      <RouteFitBounds />
      {route.legs.map((leg, legIndex) => {
        const positions = legPositions(leg);
        if (positions.length < 2) {
          return null;
        }

        const isWalk = leg.type === "walk";

        return (
          <Fragment key={`route-leg-${legIndex}`}>
            <Polyline
              positions={positions}
              pathOptions={{
                color: isWalk ? INTERMEDIATE_COLOR : TRANSIT_COLOR,
                weight: isWalk ? 4 : 5,
                opacity: 0.85,
                dashArray: isWalk ? "8 8" : undefined,
              }}
            />
            {!isWalk &&
              leg.stops?.map((stop, stopIndex) => {
                const isEndpoint = stopIndex === 0 || stopIndex === leg.stops!.length - 1;
                return (
                  <CircleMarker
                    key={`${legIndex}-${stop.stop_id}`}
                    center={[stop.lat, stop.lng]}
                    radius={isEndpoint ? 5 : 3}
                    pathOptions={{
                      color: isEndpoint ? TRANSIT_COLOR : INTERMEDIATE_COLOR,
                      fillColor: isEndpoint ? TRANSIT_COLOR : INTERMEDIATE_COLOR,
                      fillOpacity: 0.9,
                      weight: 2,
                    }}
                  />
                );
              })}
          </Fragment>
        );
      })}
    </>
  );
}
