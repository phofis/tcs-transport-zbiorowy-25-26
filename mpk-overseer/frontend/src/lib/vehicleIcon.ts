import L from "leaflet";

const MARKER_HEIGHT = 26;

function estimateIconWidth(line: string): number {
  return Math.max(MARKER_HEIGHT, 14 + line.length * 7);
}

function createVehicleIcon(line: string): L.DivIcon {
  const width = estimateIconWidth(line);
  return L.divIcon({
    className: "",
    html: `<div style="
      box-sizing: border-box;
      min-width: ${MARKER_HEIGHT}px;
      height: ${MARKER_HEIGHT}px;
      padding: 0 5px;
      border-radius: ${MARKER_HEIGHT / 2}px;
      background: #1d4ed8;
      border: 3px solid white;
      box-shadow: 0 1px 4px rgba(0,0,0,0.4);
      color: white;
      font-size: 11px;
      font-weight: 700;
      line-height: ${MARKER_HEIGHT - 6}px;
      text-align: center;
      white-space: nowrap;
    ">${line}</div>`,
    iconSize: [width, MARKER_HEIGHT],
    iconAnchor: [width / 2, MARKER_HEIGHT / 2],
  });
}

const iconCache = new Map<string, L.DivIcon>();

export function getVehicleIcon(line: string): L.DivIcon {
  let icon = iconCache.get(line);
  if (!icon) {
    icon = createVehicleIcon(line);
    iconCache.set(line, icon);
  }
  return icon;
}
