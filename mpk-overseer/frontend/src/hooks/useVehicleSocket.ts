import { useEffect, useRef, useState } from "react";

import type { Vehicle, VehiclesMessage } from "../types/vehicle";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws";
const RECONNECT_INTERVAL_MS = 2000;

function isVehiclesMessage(value: unknown): value is VehiclesMessage {
  return (
    typeof value === "object" &&
    value !== null &&
    (value as VehiclesMessage).type === "vehicles" &&
    Array.isArray((value as VehiclesMessage).data)
  );
}

function vehiclesEqual(previous: Vehicle[], next: Vehicle[]): boolean {
  if (previous.length !== next.length) {
    return false;
  }

  const nextById = new Map(next.map((vehicle) => [vehicle.vehicle_id, vehicle]));
  for (const vehicle of previous) {
    const updated = nextById.get(vehicle.vehicle_id);
    if (!updated) {
      return false;
    }
    if (
      vehicle.lat !== updated.lat ||
      vehicle.lng !== updated.lng ||
      vehicle.line !== updated.line
    ) {
      return false;
    }
  }

  return true;
}

export function useVehicleSocket(filter: string[] = []) {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const filterRef = useRef(filter);

  useEffect(() => {
    filterRef.current = filter;
  }, [filter]);

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    const connect = () => {
      if (cancelled) {
        return;
      }

      const socket = new WebSocket(WS_URL);
      socketRef.current = socket;

      socket.onopen = () => {
        if (cancelled) {
          return;
        }
        setConnected(true);
        socket.send(JSON.stringify({ filter: filterRef.current }));
      };

      socket.onmessage = (event) => {
        try {
          const message: unknown = JSON.parse(event.data as string);
          if (!isVehiclesMessage(message)) {
            return;
          }
          setVehicles((previous) =>
            vehiclesEqual(previous, message.data) ? previous : message.data,
          );
        } catch {
          // Ignore malformed messages.
        }
      };

      socket.onclose = () => {
        setConnected(false);
        if (socketRef.current === socket) {
          socketRef.current = null;
        }
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, RECONNECT_INTERVAL_MS);
        }
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
      }
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  useEffect(() => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ filter }));
    }
  }, [filter]);

  return { vehicles, connected };
}
