export interface Vehicle {
  vehicle_id: string;
  route_id: string;
  line: string;
  lat: number;
  lng: number;
  bearing: number | null;
  timestamp: number;
}

export interface VehiclesMessage {
  type: "vehicles";
  data: Vehicle[];
}
