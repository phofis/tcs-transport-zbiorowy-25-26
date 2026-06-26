from dataclasses import dataclass
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

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


class VehicleOut(BaseModel):
    vehicle_id: str
    route_id: str
    line: str
    lat: float
    lng: float
    bearing: float | None = None
    timestamp: int


class RouteRequest(BaseModel):
    start_stop_id: str | None = None
    start_lat: float | None = None
    start_lng: float | None = None
    end_stop_id: str | None = None
    end_lat: float | None = None
    end_lng: float | None = None
    departure_ts: int
    max_walk_time_mins: int = Field(default=5, ge=0, le=30)

    @model_validator(mode="after")
    def validate_endpoints(self) -> Self:
        start_stop = self.start_stop_id is not None
        start_point = self.start_lat is not None or self.start_lng is not None
        if start_stop == start_point:
            raise ValueError("Provide exactly one of start_stop_id or start_lat+start_lng")
        if start_point and (self.start_lat is None or self.start_lng is None):
            raise ValueError("start_lat and start_lng must both be set")

        end_stop = self.end_stop_id is not None
        end_point = self.end_lat is not None or self.end_lng is not None
        if end_stop == end_point:
            raise ValueError("Provide exactly one of end_stop_id or end_lat+end_lng")
        if end_point and (self.end_lat is None or self.end_lng is None):
            raise ValueError("end_lat and end_lng must both be set")
        return self


class RouteStopOut(BaseModel):
    stop_id: str
    name: str
    lat: float
    lng: float


class RouteLegOut(BaseModel):
    type: Literal["walk", "transit"]
    from_stop_id: str | None = None
    to_stop_id: str | None = None
    from_name: str | None = None
    to_name: str | None = None
    from_lat: float | None = None
    from_lng: float | None = None
    to_lat: float | None = None
    to_lng: float | None = None
    line: str | None = None
    departure_ts: int | None = None
    arrival_ts: int | None = None
    duration_seconds: int | None = None
    stops: list[RouteStopOut] = Field(default_factory=list)


class RouteResponse(BaseModel):
    found: bool
    arrival_ts: int | None = None
    legs: list[RouteLegOut] = Field(default_factory=list)
