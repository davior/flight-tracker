from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from app.config import Settings
from app.services.live_flight_provider import LiveFlightCapabilities, LiveFlightProviderError, LiveFlightRecord
from app.utils.geo import center_from_bounds, haversine_distance_km


TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
STATES_URL = "https://opensky-network.org/api/states/all"
TOKEN_REFRESH_MARGIN = 30
MAX_HISTORY_MINUTES = 60
HISTORY_STEP_MINUTES = 1


class OpenSkyLiveFlightProvider:
    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self.settings = settings
        self.session = session or requests.Session()
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    def close(self) -> None:
        self.session.close()

    @property
    def capabilities(self) -> LiveFlightCapabilities:
        supports_history = bool(self.settings.opensky_client_id and self.settings.opensky_client_secret)
        return LiveFlightCapabilities(
            provider="opensky",
            supports_history=supports_history,
            max_history_minutes=MAX_HISTORY_MINUTES if supports_history else 0,
            history_step_minutes=HISTORY_STEP_MINUTES,
        )

    def get_flight_by_icao24(
        self,
        icao24: str,
        time_seconds: int | None = None,
    ) -> LiveFlightRecord | None:
        params: dict[str, str | int] = {"icao24": icao24}
        if time_seconds is not None:
            params["time"] = time_seconds

        payload = self._fetch_states(params)
        for state in payload.get("states") or []:
            parsed = self._parse_state(state, 0.0, 0.0)
            if parsed is not None:
                return parsed
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
        params: dict[str, float | int] = {
            "lamin": south,
            "lomin": west,
            "lamax": north,
            "lomax": east,
        }
        if time_seconds is not None:
            params["time"] = time_seconds

        payload = self._fetch_states(params)

        flights: list[LiveFlightRecord] = []
        for state in payload.get("states") or []:
            parsed = self._parse_state(state, center_lat, center_lon)
            if parsed is not None:
                flights.append(parsed)

        flights.sort(key=lambda item: item.distance_km)
        return flights

    def _fetch_states(self, params: dict[str, float | int]) -> dict:
        headers = self._build_headers()
        try:
            response = self.session.get(STATES_URL, params=params, headers=headers, timeout=15)
        except requests.RequestException as exc:
            raise LiveFlightProviderError(
                "OpenSky request failed",
                code="provider_unavailable",
                provider="opensky",
                retryable=True,
            ) from exc

        if response.status_code == 401 and self.settings.opensky_client_id and self.settings.opensky_client_secret:
            self._refresh_token(force=True)
            headers = self._build_headers()
            try:
                response = self.session.get(STATES_URL, params=params, headers=headers, timeout=15)
            except requests.RequestException as exc:
                raise LiveFlightProviderError(
                    "OpenSky request failed",
                    code="provider_unavailable",
                    provider="opensky",
                    retryable=True,
                ) from exc

        if response.status_code == 429:
            raise LiveFlightProviderError(
                "OpenSky responded with status 429",
                code="rate_limited",
                provider="opensky",
                retryable=True,
            )
        if response.status_code == 401:
            raise LiveFlightProviderError(
                "OpenSky authentication failed",
                code="authentication_failed",
                provider="opensky",
                retryable=False,
            )
        if response.status_code != 200:
            raise LiveFlightProviderError(
                f"OpenSky responded with status {response.status_code}",
                code="provider_unavailable",
                provider="opensky",
                retryable=response.status_code >= 500,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise LiveFlightProviderError(
                "OpenSky returned invalid JSON",
                code="invalid_response",
                provider="opensky",
                retryable=False,
            ) from exc

    def _build_headers(self) -> dict[str, str]:
        token = self._get_token()
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def _get_token(self) -> str | None:
        if not self.settings.opensky_client_id or not self.settings.opensky_client_secret:
            return None

        if self._token and self._token_expires_at and datetime.now(timezone.utc) < self._token_expires_at:
            return self._token

        return self._refresh_token()

    def _refresh_token(self, force: bool = False) -> str:
        if (
            not force
            and self._token
            and self._token_expires_at
            and datetime.now(timezone.utc) < self._token_expires_at
        ):
            return self._token

        try:
            response = self.session.post(
                TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.opensky_client_id,
                    "client_secret": self.settings.opensky_client_secret,
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            raise LiveFlightProviderError(
                "OpenSky authentication failed",
                code="authentication_failed",
                provider="opensky",
                retryable=False,
            ) from exc

        if response.status_code != 200:
            raise LiveFlightProviderError(
                f"OpenSky authentication failed with status {response.status_code}",
                code="authentication_failed",
                provider="opensky",
                retryable=False,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LiveFlightProviderError(
                "OpenSky authentication returned invalid JSON",
                code="invalid_response",
                provider="opensky",
                retryable=False,
            ) from exc

        access_token = data.get("access_token")
        if not access_token:
            raise LiveFlightProviderError(
                "OpenSky authentication response did not contain an access token",
                code="invalid_response",
                provider="opensky",
                retryable=False,
            )

        expires_in = int(data.get("expires_in", 1800))
        self._token = access_token
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=max(expires_in - TOKEN_REFRESH_MARGIN, 1)
        )
        return access_token

    def _parse_state(
        self,
        state: list,
        origin_lat: float,
        origin_lon: float,
    ) -> LiveFlightRecord | None:
        if len(state) < 17:
            return None

        longitude = state[5]
        latitude = state[6]
        if latitude is None or longitude is None:
            return None

        distance = haversine_distance_km(origin_lat, origin_lon, latitude, longitude)

        callsign = state[1].strip() if isinstance(state[1], str) else None
        baro_altitude = state[7]
        geo_altitude = state[13] if len(state) > 13 else None
        altitude = geo_altitude if geo_altitude is not None else baro_altitude

        return LiveFlightRecord(
            icao24=str(state[0]).lower(),
            callsign=callsign or None,
            origin_country=state[2],
            longitude=float(longitude),
            latitude=float(latitude),
            altitude=float(altitude) if altitude is not None else None,
            velocity=float(state[9]) if state[9] is not None else None,
            heading=float(state[10]) if state[10] is not None else None,
            vertical_rate=float(state[11]) if state[11] is not None else None,
            last_contact=int(state[4]) if state[4] is not None else None,
            distance_km=round(distance, 3),
        )


OpenSkyClient = OpenSkyLiveFlightProvider
