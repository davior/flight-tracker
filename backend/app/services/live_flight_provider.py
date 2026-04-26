from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class LiveFlightRecord:
    icao24: str
    callsign: str | None
    origin_country: str | None
    latitude: float
    longitude: float
    altitude: float | None
    velocity: float | None
    heading: float | None
    vertical_rate: float | None
    last_contact: int | None
    distance_km: float


@dataclass(slots=True)
class LiveFlightCapabilities:
    provider: str
    supports_history: bool
    max_history_minutes: int
    history_step_minutes: int
    supports_trajectory: bool = False


class LiveFlightProviderError(RuntimeError):
    def __init__(self, message: str, *, code: str, provider: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.provider = provider
        self.retryable = retryable


class LiveFlightProvider(Protocol):
    @property
    def capabilities(self) -> LiveFlightCapabilities: ...

    def close(self) -> None: ...

    def get_flights_in_bounds(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        time_seconds: int | None = None,
    ) -> list[LiveFlightRecord]: ...

    def get_flight_by_icao24(
        self,
        icao24: str,
        time_seconds: int | None = None,
    ) -> LiveFlightRecord | None: ...
