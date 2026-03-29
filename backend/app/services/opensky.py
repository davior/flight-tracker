from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests

from app.config import Settings
from app.utils.geo import bounding_box, haversine_distance_km


TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
STATES_URL = "https://opensky-network.org/api/states/all"
TOKEN_REFRESH_MARGIN = 30


class OpenSkyError(RuntimeError):
    """Raised when the OpenSky API cannot be queried safely."""


@dataclass(slots=True)
class NearbyFlight:
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


class OpenSkyClient:
    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self.settings = settings
        self.session = session or requests.Session()
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    def close(self) -> None:
        self.session.close()

    def get_nearby_flights(self, lat: float, lon: float, radius_km: float) -> list[NearbyFlight]:
        min_lat, min_lon, max_lat, max_lon = bounding_box(lat, lon, radius_km)
        payload = self._fetch_states(
            {
                "lamin": min_lat,
                "lomin": min_lon,
                "lamax": max_lat,
                "lomax": max_lon,
            }
        )

        flights: list[NearbyFlight] = []
        for state in payload.get("states") or []:
            parsed = self._parse_state(state, lat, lon, radius_km)
            if parsed is not None:
                flights.append(parsed)

        flights.sort(key=lambda item: item.distance_km)
        return flights

    def _fetch_states(self, params: dict[str, float]) -> dict:
        headers = self._build_headers()
        try:
            response = self.session.get(STATES_URL, params=params, headers=headers, timeout=15)
        except requests.RequestException as exc:
            raise OpenSkyError("OpenSky request failed") from exc

        if response.status_code == 401 and self.settings.opensky_client_id and self.settings.opensky_client_secret:
            self._refresh_token(force=True)
            headers = self._build_headers()
            try:
                response = self.session.get(STATES_URL, params=params, headers=headers, timeout=15)
            except requests.RequestException as exc:
                raise OpenSkyError("OpenSky request failed") from exc

        if response.status_code != 200:
            raise OpenSkyError(f"OpenSky responded with status {response.status_code}")

        try:
            return response.json()
        except ValueError as exc:
            raise OpenSkyError("OpenSky returned invalid JSON") from exc

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
            raise OpenSkyError("OpenSky authentication failed") from exc

        if response.status_code != 200:
            raise OpenSkyError(f"OpenSky authentication failed with status {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise OpenSkyError("OpenSky authentication returned invalid JSON") from exc

        access_token = data.get("access_token")
        if not access_token:
            raise OpenSkyError("OpenSky authentication response did not contain an access token")

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
        radius_km: float,
    ) -> NearbyFlight | None:
        if len(state) < 17:
            return None

        longitude = state[5]
        latitude = state[6]
        if latitude is None or longitude is None:
            return None

        distance = haversine_distance_km(origin_lat, origin_lon, latitude, longitude)
        if distance > radius_km:
            return None

        callsign = state[1].strip() if isinstance(state[1], str) else None
        baro_altitude = state[7]
        geo_altitude = state[13] if len(state) > 13 else None
        altitude = geo_altitude if geo_altitude is not None else baro_altitude

        return NearbyFlight(
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
