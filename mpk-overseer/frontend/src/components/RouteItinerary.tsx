import { Bus, ChevronDown, ChevronRight, Footprints, TramFront } from "lucide-react";
import { useMemo, useState } from "react";

import { useApp } from "@/context/AppContext";
import { formatEpochWarsaw } from "@/lib/departureTime";
import { cn } from "@/lib/utils";
import type { RouteLeg, RouteResponse } from "@/types/route";
import type { StopKind } from "@/types/stop";

function formatDuration(seconds: number): string {
  const mins = Math.max(1, Math.round(seconds / 60));
  return `Ok. ${mins} min`;
}

function transitDurationMinutes(leg: RouteLeg): number {
  if (leg.departure_ts == null || leg.arrival_ts == null) {
    return 0;
  }
  return Math.max(1, Math.round((leg.arrival_ts - leg.departure_ts) / 60));
}

function VehicleIcon({ kind }: { kind: StopKind }) {
  if (kind === "tram") {
    return <TramFront className="h-4 w-4 text-muted-foreground" />;
  }
  return <Bus className="h-4 w-4 text-muted-foreground" />;
}

function TimelineRail({
  variant,
  showBottom = true,
}: {
  variant: "walk" | "transit";
  showBottom?: boolean;
}) {
  return (
    <div className="flex w-8 shrink-0 flex-col items-center">
      <div
        className={cn(
          "h-3 w-3 rounded-full border-2 bg-background",
          variant === "transit" ? "border-primary" : "border-muted-foreground",
        )}
      />
      {showBottom && (
        <div
          className={cn(
            "min-h-6 w-0.5 flex-1",
            variant === "transit" ? "bg-primary/70" : "border-l-2 border-dashed border-muted-foreground/50",
          )}
        />
      )}
    </div>
  );
}

function WalkLegRow({ leg }: { leg: RouteLeg }) {
  const durationLabel =
    leg.duration_seconds != null ? formatDuration(leg.duration_seconds) : "Pieszo";

  return (
    <div className="flex gap-2">
      <TimelineRail variant="walk" />
      <div className="flex flex-1 items-start gap-2 pb-4 pt-0.5">
        <Footprints className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
        <div className="text-sm">
          <div className="font-medium">Pieszo</div>
          <div className="text-muted-foreground">{durationLabel}</div>
          <div className="text-muted-foreground">
            {leg.from_name ?? "?"} → {leg.to_name ?? "?"}
          </div>
        </div>
      </div>
    </div>
  );
}

function TransitLegRow({
  leg,
  vehicleKind,
}: {
  leg: RouteLeg;
  vehicleKind: StopKind;
}) {
  const [expanded, setExpanded] = useState(false);
  const stops = leg.stops ?? [];
  const intermediate = stops.length > 2 ? stops.slice(1, -1) : [];
  const intermediateCount = intermediate.length;
  const durationMins = transitDurationMinutes(leg);

  return (
    <div className="flex gap-2">
      <TimelineRail variant="transit" />
      <div className="flex-1 pb-4">
        <div className="flex items-start gap-2">
          <VehicleIcon kind={vehicleKind} />
          <div className="min-w-0 flex-1">
            {leg.departure_ts != null && (
              <div className="flex items-baseline gap-2">
                <span className="text-sm font-semibold text-emerald-700">
                  {formatEpochWarsaw(leg.departure_ts)}
                </span>
                <span className="truncate text-sm font-medium">{leg.from_name}</span>
              </div>
            )}

            <div className="mt-1 flex flex-wrap items-center gap-2">
              {leg.line && (
                <span className="inline-flex min-w-[2rem] items-center justify-center rounded bg-primary px-2 py-0.5 text-xs font-bold text-primary-foreground">
                  {leg.line}
                </span>
              )}
              <span className="truncate text-sm text-muted-foreground">→ {leg.to_name}</span>
            </div>

            {intermediateCount > 0 && (
              <button
                type="button"
                className="mt-2 flex w-full items-center gap-1 text-left text-sm text-muted-foreground hover:text-foreground"
                onClick={() => setExpanded((value) => !value)}
              >
                {expanded ? (
                  <ChevronDown className="h-4 w-4 shrink-0" />
                ) : (
                  <ChevronRight className="h-4 w-4 shrink-0" />
                )}
                <span>
                  {durationMins} min · {intermediateCount}{" "}
                  {intermediateCount === 1 ? "przystanek" : "przystanków"}
                </span>
              </button>
            )}

            {expanded && intermediateCount > 0 && (
              <ul className="mt-1 space-y-0.5 border-l border-muted pl-3">
                {intermediate.map((stop) => (
                  <li key={stop.stop_id} className="text-xs text-muted-foreground">
                    {stop.name}
                  </li>
                ))}
              </ul>
            )}

            {leg.arrival_ts != null && (
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-sm font-semibold">{formatEpochWarsaw(leg.arrival_ts)}</span>
                <span className="truncate text-sm">{leg.to_name}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function EndpointRow({
  label,
  timeTs,
  isLast = false,
}: {
  label: string;
  timeTs?: number | null;
  isLast?: boolean;
}) {
  return (
    <div className="flex gap-2">
      <div className="flex w-8 shrink-0 flex-col items-center">
        <div
          className={cn(
            "h-3 w-3 rounded-full border-2 bg-background",
            isLast ? "border-foreground" : "border-primary",
          )}
        />
        {!isLast && <div className="min-h-2 w-0.5 flex-1 bg-primary/70" />}
      </div>
      <div className={cn("flex-1", !isLast && "pb-2")}>
        {timeTs != null && (
          <span className="mr-2 text-sm font-semibold">{formatEpochWarsaw(timeTs)}</span>
        )}
        <span className="text-sm font-medium">{label}</span>
      </div>
    </div>
  );
}

export default function RouteItinerary({ route }: { route: RouteResponse }) {
  const { stops } = useApp();

  const stopKindById = useMemo(() => {
    const map = new Map<string, StopKind>();
    for (const stop of stops) {
      map.set(stop.stop_id, stop.kind);
    }
    return map;
  }, [stops]);

  if (!route.found || route.legs.length === 0) {
    return null;
  }

  const firstLeg = route.legs[0];
  const lastLeg = route.legs[route.legs.length - 1];

  return (
    <div className="space-y-0">
      <EndpointRow
        label={firstLeg.from_name ?? "Start"}
        timeTs={firstLeg.departure_ts ?? undefined}
      />

      {route.legs.map((leg, index) =>
        leg.type === "walk" ? (
          <WalkLegRow key={`walk-${index}`} leg={leg} />
        ) : (
          <TransitLegRow
            key={`transit-${index}`}
            leg={leg}
            vehicleKind={stopKindById.get(leg.from_stop_id ?? "") ?? "bus"}
          />
        ),
      )}

      <EndpointRow
        label={lastLeg.to_name ?? "Koniec"}
        timeTs={route.arrival_ts}
        isLast
      />
    </div>
  );
}
