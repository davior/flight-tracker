from __future__ import annotations

import pytest

from app.config import Settings
from app.services.adsbx import ADSBxLiveFlightProvider
from app.services.live_flight_provider_factory import create_live_flight_provider
from app.services.opensky import OpenSkyLiveFlightProvider


def test_factory_creates_opensky_provider():
    provider = create_live_flight_provider(Settings(live_flight_provider="opensky"))
    assert isinstance(provider, OpenSkyLiveFlightProvider)
    provider.close()


def test_factory_creates_adsbx_provider():
    provider = create_live_flight_provider(
        Settings(
            live_flight_provider="adsbx",
            adsbx_api_key="demo-key",
        )
    )
    assert isinstance(provider, ADSBxLiveFlightProvider)
    provider.close()


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unsupported live-flight provider"):
        create_live_flight_provider(Settings(live_flight_provider="unknown"))


def test_factory_requires_adsbx_api_key():
    with pytest.raises(ValueError, match="ADSBX_API_KEY must be set"):
        create_live_flight_provider(Settings(live_flight_provider="adsbx", adsbx_api_key=None))
