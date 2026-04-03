from __future__ import annotations

from app.config import Settings
from app.services.adsbx import ADSBxLiveFlightProvider
from app.services.live_flight_provider import LiveFlightProvider
from app.services.opensky import OpenSkyLiveFlightProvider


def create_live_flight_provider(settings: Settings) -> LiveFlightProvider:
    provider_name = settings.live_flight_provider.strip().lower()
    if provider_name == "opensky":
        return OpenSkyLiveFlightProvider(settings)
    if provider_name == "adsbx":
        if not settings.adsbx_api_key:
            raise ValueError("ADSBX_API_KEY must be set when LIVE_FLIGHT_PROVIDER=adsbx")
        return ADSBxLiveFlightProvider(settings)
    raise ValueError(f"Unsupported live-flight provider: {settings.live_flight_provider}")
