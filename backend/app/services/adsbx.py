from __future__ import annotations

from dataclasses import dataclass

import requests

from app.config import Settings
from app.services.live_flight_provider import LiveFlightCapabilities, LiveFlightProviderError, LiveFlightRecord
from app.utils.geo import center_from_bounds, haversine_distance_km, radius_from_bounds


MAX_ADSBX_RADIUS_KM = 185.2
HISTORY_STEP_MINUTES = 1


@dataclass(slots=True)
class ADSBxLiveFlightProvider:
    settings: Settings
    session: requests.Session | None = None

    def __post_init__(self) -> None:
        self.session = self.session or requests.Session()

    def close(self) -> None:
        if self.session is not None:
            self.session.close()

    @property
    def capabilities(self) -> LiveFlightCapabilities:
        return LiveFlightCapabilities(
            provider="adsbx",
            supports_history=False,
            max_history_minutes=0,
            history_step_minutes=HISTORY_STEP_MINUTES,
            supports_trajectory=False,
        )

    def get_flight_by_icao24(
        self,
        icao24: str,
        time_seconds: int | None = None,
    ) -> LiveFlightRecord | None:
        # ADS-B Exchange does not support historical position lookup
        return None

    def get_flights_in_bounds(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        time_seconds: int | None = None,
    ) -> list[LiveFlightRecord]:
        center_lat, center_lon = center_from_bounds(north, south, east, west)
        radius_km = radius_from_bounds(north, south, east, west)
        if radius_km > MAX_ADSBX_RADIUS_KM:
            raise LiveFlightProviderError(
                f"ADSBX nearby lookups are limited to {round(MAX_ADSBX_RADIUS_KM, 1)} km",
                code="provider_unavailable",
                provider="adsbx",
                retryable=False,
            )

        payload = self._fetch_aircraft(center_lat, center_lon, radius_km)
        flights: list[LiveFlightRecord] = []
        for aircraft in payload.get("ac") or payload.get("aircraft") or []:
            parsed = self._parse_aircraft(aircraft, center_lat, center_lon)
            if parsed is not None:
                flights.append(parsed)
        flights.sort(key=lambda item: item.distance_km)
        return flights

    def _fetch_aircraft(self, latitude: float, longitude: float, radius_km: float) -> dict:
        assert self.session is not None
        radius_nm = min(radius_km / 1.852, 100.0)
        base_url = self.settings.adsbx_api_base_url.rstrip("/")
        url = f"{base_url}/lat/{latitude}/lon/{longitude}/dist/{radius_nm}/"
        try:
            response = self.session.get(
                url,
                headers={"api-auth": self.settings.adsbx_api_key or ""},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise LiveFlightProviderError(
                "ADSBX request failed",
                code="provider_unavailable",
                provider="adsbx",
                retryable=True,
            ) from exc

        if response.status_code in {401, 403}:
            raise LiveFlightProviderError(
                "ADSBX authentication failed",
                code="authentication_failed",
                provider="adsbx",
                retryable=False,
            )
        if response.status_code == 429:
            raise LiveFlightProviderError(
                "ADSBX responded with status 429",
                code="rate_limited",
                provider="adsbx",
                retryable=True,
            )
        if response.status_code != 200:
            raise LiveFlightProviderError(
                f"ADSBX responded with status {response.status_code}",
                code="provider_unavailable",
                provider="adsbx",
                retryable=response.status_code >= 500,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise LiveFlightProviderError(
                "ADSBX returned invalid JSON",
                code="invalid_response",
                provider="adsbx",
                retryable=False,
            ) from exc

    def _parse_aircraft(self, aircraft: dict, origin_lat: float, origin_lon: float) -> LiveFlightRecord | None:
        raw_hex = aircraft.get("hex")
        if not isinstance(raw_hex, str):
            return None
        icao24 = raw_hex.lower().lstrip("~")
        if len(icao24) != 6:
            return None

        latitude = aircraft.get("lat")
        longitude = aircraft.get("lon")
        if latitude is None or longitude is None:
            return None

        callsign = aircraft.get("flight")
        if isinstance(callsign, str):
            callsign = callsign.strip() or None
        else:
            callsign = None

        altitude = aircraft.get("alt_geom")
        if altitude is None:
            altitude = aircraft.get("alt_baro")

        last_contact = aircraft.get("seen_pos")
        if last_contact is None:
            last_contact = aircraft.get("seen")

        try:
            distance = haversine_distance_km(origin_lat, origin_lon, float(latitude), float(longitude))
        except (TypeError, ValueError):
            return None

        return LiveFlightRecord(
            icao24=icao24,
            callsign=callsign,
            origin_country=None,
            latitude=float(latitude),
            longitude=float(longitude),
            altitude=self._coerce_float(altitude),
            velocity=self._coerce_float(aircraft.get("gs")),
            heading=self._coerce_float(aircraft.get("track")),
            vertical_rate=self._coerce_float(aircraft.get("baro_rate")),
            last_contact=self._coerce_last_contact(last_contact),
            distance_km=round(distance, 3),
        )

    @staticmethod
    def _coerce_float(value: object) -> float | None:
        if value in (None, "ground"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_last_contact(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
