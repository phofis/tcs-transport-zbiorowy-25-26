import { format } from "date-fns";
import { pl } from "date-fns/locale";
import { CalendarIcon, MapPin, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Slider } from "@/components/ui/slider";
import { useApp } from "@/context/AppContext";
import { formatEpochWarsaw } from "@/lib/departureTime";
import { formatStopName, stopMatchesQuery } from "@/lib/formatStopName";
import { cn } from "@/lib/utils";
import RouteItinerary from "./RouteItinerary";
import type { Endpoint } from "@/types/search";
import type { Stop } from "@/types/stop";

const CUSTOM_POINT_LABEL = "Własny punkt";

function endpointLabel(endpoint: Endpoint | null): string {
  if (!endpoint) {
    return "";
  }
  if (endpoint.kind === "point") {
    return CUSTOM_POINT_LABEL;
  }
  return formatStopName(endpoint.stop);
}

interface EndpointFieldProps {
  label: string;
  endpoint: Endpoint | null;
  pickModeActive: boolean;
  onSelect: (endpoint: Endpoint | null) => void;
  onPickOnMap: () => void;
  stops: Stop[];
}

function EndpointField({
  label,
  endpoint,
  pickModeActive,
  onSelect,
  onPickOnMap,
  stops,
}: EndpointFieldProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const displayValue = endpoint?.kind === "point" && !open ? CUSTOM_POINT_LABEL : query || endpointLabel(endpoint);

  const filteredStops = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return stops.slice(0, 50);
    }
    return stops.filter((stop) => stopMatchesQuery(stop, query)).slice(0, 50);
  }, [query, stops]);

  const handleInputChange = (value: string) => {
    if (endpoint?.kind === "point") {
      onSelect(null);
    }
    setQuery(value);
    setOpen(true);
  };

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="flex gap-2">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Input
              placeholder="Szukaj przystanku…"
              value={displayValue}
              onChange={(event) => handleInputChange(event.target.value)}
              onFocus={() => {
                if (endpoint?.kind === "point") {
                  onSelect(null);
                  setQuery("");
                }
                setOpen(true);
              }}
            />
          </PopoverTrigger>
          <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
            <Command shouldFilter={false}>
              <CommandInput
                placeholder="Szukaj przystanku…"
                value={query}
                onValueChange={handleInputChange}
              />
              <CommandList>
                <CommandEmpty>Brak wyników</CommandEmpty>
                <CommandGroup>
                  {filteredStops.map((stop) => (
                    <CommandItem
                      key={stop.stop_id}
                      value={stop.stop_id}
                      onSelect={() => {
                        onSelect({ kind: "stop", stop });
                        setQuery(formatStopName(stop));
                        setOpen(false);
                      }}
                    >
                      {formatStopName(stop)}
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
        <Button
          type="button"
          variant={pickModeActive ? "default" : "outline"}
          size="icon"
          title="Wybierz na mapie"
          onClick={onPickOnMap}
        >
          <MapPin className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

export default function Sidebar() {
  const {
    stops,
    startEndpoint,
    endEndpoint,
    pickMode,
    maxWalkMins,
    departureDate,
    departureTime,
    route,
    routeLoading,
    routeError,
    setStartEndpoint,
    setEndEndpoint,
    setPickMode,
    setMaxWalkMins,
    setDepartureDate,
    setDepartureTime,
    searchRoute,
  } = useApp();

  const [calendarOpen, setCalendarOpen] = useState(false);

  return (
    <aside className="flex h-full w-[360px] shrink-0 flex-col border-r bg-background">
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Wyszukaj połączenie</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <EndpointField
              label="Skąd"
              endpoint={startEndpoint}
              pickModeActive={pickMode === "start"}
              onSelect={setStartEndpoint}
              onPickOnMap={() => setPickMode(pickMode === "start" ? null : "start")}
              stops={stops}
            />
            <EndpointField
              label="Dokąd"
              endpoint={endEndpoint}
              pickModeActive={pickMode === "end"}
              onSelect={setEndEndpoint}
              onPickOnMap={() => setPickMode(pickMode === "end" ? null : "end")}
              stops={stops}
            />

            <div className="space-y-2">
              <Label>Data odjazdu</Label>
              <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn("w-full justify-start text-left font-normal")}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {format(departureDate, "PPP", { locale: pl })}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={departureDate}
                    onSelect={(date) => {
                      if (date) {
                        setDepartureDate(date);
                        setCalendarOpen(false);
                      }
                    }}
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div className="space-y-2">
              <Label htmlFor="departure-time">Godzina odjazdu</Label>
              <Input
                id="departure-time"
                type="time"
                value={departureTime}
                onChange={(event) => setDepartureTime(event.target.value)}
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Maks. czas pieszo (jeden odcinek)</Label>
                <span className="text-sm text-muted-foreground">{maxWalkMins} min</span>
              </div>
              <Slider
                min={0}
                max={30}
                step={1}
                value={[maxWalkMins]}
                onValueChange={(value) => setMaxWalkMins(value[0] ?? 5)}
              />
            </div>

            <Button className="w-full" onClick={() => void searchRoute()} disabled={routeLoading}>
              <Search className="mr-2 h-4 w-4" />
              {routeLoading ? "Szukam…" : "Szukaj"}
            </Button>

            {pickMode && (
              <p className="text-sm text-muted-foreground">
                Kliknij na mapie, aby ustawić punkt {pickMode === "start" ? "startowy" : "docelowy"}.
              </p>
            )}
            {routeError && <p className="text-sm text-destructive">{routeError}</p>}
          </CardContent>
        </Card>

        {route?.found && route.legs.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Trasa</CardTitle>
              {route.arrival_ts != null && (
                <p className="text-sm text-muted-foreground">
                  Przyjazd: {formatEpochWarsaw(route.arrival_ts, true)}
                </p>
              )}
            </CardHeader>
            <CardContent>
              <RouteItinerary route={route} />
            </CardContent>
          </Card>
        )}
      </div>
    </aside>
  );
}
