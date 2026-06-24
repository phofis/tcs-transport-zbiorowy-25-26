import { useEffect, useState } from "react";

import { fetchStopDepartures } from "../lib/api";
import { formatDepartureTime } from "../lib/formatDeparture";
import type { StopDepartures } from "../types/departure";
import type { Stop, StopKind } from "../types/stop";

const KIND_BADGE_COLORS: Record<StopKind, string> = {
  tram: "#5b4fc7",
  bus: "#e67e22",
  mixed: "#8e44ad",
};

const KIND_LABELS: Record<StopKind, string> = {
  tram: "tram",
  bus: "bus",
  mixed: "mixed",
};

function formatStopLabel(stop: Stop): string {
  if (stop.platform) {
    return `${stop.name} ${stop.platform}`;
  }
  return stop.name;
}

interface StopDeparturesPopupProps {
  stop: Stop;
}

export default function StopDeparturesPopup({ stop }: StopDeparturesPopupProps) {
  const [data, setData] = useState<StopDepartures | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchStopDepartures(stop.stop_id)
      .then((departures) => {
        if (!cancelled) {
          setData(departures);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Nie udało się załadować odjazdów",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [stop.stop_id]);

  if (error) {
    return <div className="stop-departures-popup__message stop-departures-popup__message--error">{error}</div>;
  }

  if (!data) {
    return <div className="stop-departures-popup__message">Ładowanie odjazdów…</div>;
  }

  const nowTs = data.generated_ts;

  return (
    <div className="stop-departures-popup">
      <div className="stop-departures-popup__header">
        <span className="stop-departures-popup__title">{formatStopLabel(stop)}</span>
        <span
          className="stop-departures-popup__kind"
          style={{ backgroundColor: KIND_BADGE_COLORS[stop.kind] }}
        >
          {KIND_LABELS[stop.kind]}
        </span>
      </div>

      {data.lines.length === 0 ? (
        <div className="stop-departures-popup__message">
          Brak odjazdów w najbliższych 4 godzinach
        </div>
      ) : (
        <div className="stop-departures-popup__lines">
          {data.lines.map((line) => (
            <div key={line.line} className="stop-departures-popup__row">
              <span
                className="stop-departures-popup__line-badge"
                style={{ backgroundColor: KIND_BADGE_COLORS[line.kind] }}
              >
                {line.line}
              </span>
              <div className="stop-departures-popup__times">
                {line.departures.map((departure) => (
                  <span
                    key={`${departure.trip_id}-${departure.departure_ts}`}
                    className="stop-departures-popup__time"
                  >
                    {formatDepartureTime(departure.departure_ts, nowTs)}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
