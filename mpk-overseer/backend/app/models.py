from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

StopKind = Literal["tram", "bus", "mixed"]


@dataclass(frozen=True)
class Stop:
    stop_id: str
    name: str
    lat: float
    lng: float
    platform: str | None = None


@dataclass(frozen=True)
class RouteInfo:
    route_short_name: str
    route_type: int


@dataclass(frozen=True)
class TripInfo:
    route_id: str
    service_id: str
    trip_headsign: str | None


@dataclass(frozen=True)
class StopTime:
    stop_id: str
    arrival_time: str | None
    departure_time: str | None
    stop_sequence: int


@dataclass(frozen=True)
class Connection:
    departure_stop: str
    arrival_stop: str
    departure_ts: int
    arrival_ts: int
    trip_id: str
    route_short_name: str
    trip_headsign: str | None


class StopOut(BaseModel):
    stop_id: str
    name: str
    lat: float
    lng: float
    kind: StopKind
    platform: str | None = None


class DepartureOut(BaseModel):
    departure_ts: int
    trip_id: str
    headsign: str | None = None


class LineDeparturesOut(BaseModel):
    line: str
    kind: StopKind
    departures: list[DepartureOut]


class StopDeparturesOut(BaseModel):
    stop_id: str
    generated_ts: int
    lines: list[LineDeparturesOut]
