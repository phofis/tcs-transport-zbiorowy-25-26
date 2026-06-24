import L from "leaflet";
import { Marker, Popup } from "react-leaflet";

import type { Stop, StopKind } from "../types/stop";
import StopDeparturesPopup from "./StopDeparturesPopup";

const KIND_COLORS: Record<StopKind, string> = {
  tram: "#5b4fc7",
  bus: "#e67e22",
  mixed: "linear-gradient(90deg, #5b4fc7 50%, #e67e22 50%)",
};

const MARKER_SIZE = 20;
const MARKER_ANCHOR = MARKER_SIZE / 2;

function createStopIcon(kind: StopKind): L.DivIcon {
  const background = KIND_COLORS[kind];
  return L.divIcon({
    className: "",
    html: `<div style="
      width: ${MARKER_SIZE}px;
      height: ${MARKER_SIZE}px;
      border-radius: 50%;
      background: ${background};
      border: 4.5px solid white;
      box-shadow: 0 0 6px rgba(0,0,0,0.4);
    "></div>`,
    iconSize: [MARKER_SIZE, MARKER_SIZE],
    iconAnchor: [MARKER_ANCHOR, MARKER_ANCHOR],
  });
}

const iconCache = new Map<StopKind, L.DivIcon>();

function getStopIcon(kind: StopKind): L.DivIcon {
  let icon = iconCache.get(kind);
  if (!icon) {
    icon = createStopIcon(kind);
    iconCache.set(kind, icon);
  }
  return icon;
}

interface StopMarkerProps {
  stop: Stop;
}

export default function StopMarker({ stop }: StopMarkerProps) {
  return (
    <Marker
      position={[stop.lat, stop.lng]}
      icon={getStopIcon(stop.kind)}
    >
      <Popup minWidth={320} maxHeight={360} className="stop-departures-leaflet-popup">
        <StopDeparturesPopup stop={stop} />
      </Popup>
    </Marker>
  );
}
