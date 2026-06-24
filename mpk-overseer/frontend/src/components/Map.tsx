import { MapContainer, TileLayer } from "react-leaflet";

import StopMarkersLayer from "./StopMarkersLayer";
import VehicleMarkersLayer from "./VehicleMarkersLayer";

const KRAKOW_CENTER: [number, number] = [50.0647, 19.945];
const DEFAULT_ZOOM = 14;

export default function Map() {
  return (
    <MapContainer
      center={KRAKOW_CENTER}
      zoom={DEFAULT_ZOOM}
      className="h-full w-full"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <VehicleMarkersLayer />
      <StopMarkersLayer />
    </MapContainer>
  );
}
