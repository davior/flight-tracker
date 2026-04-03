from __future__ import annotations

import pytest

from app.config import Settings
from app.services.adsbx import ADSBxLiveFlightProvider
from app.services.live_flight_provider import LiveFlightProviderError
from app.services.opensky import OpenSkyLiveFlightProvider


class FakeResponse:
    def __init__(self, *, status_code: int, json_payload=None, json_error: Exception | None = None):
        self.status_code = status_code
        self._json_payload = json_payload
        self._json_error = json_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._json_payload


class FakeSession:
    def __init__(self, *, get_responses=None, post_responses=None, get_error: Exception | None = None, post_error: Exception | None = None):
        self.get_responses = list(get_responses or [])
        self.post_responses = list(post_responses or [])
        self.get_error = get_error
        self.post_error = post_error
        self.get_calls = []
        self.post_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        if self.get_error is not None:
            raise self.get_error
        return self.get_responses.pop(0)

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        if self.post_error is not None:
            raise self.post_error
        return self.post_responses.pop(0)

    def close(self):
        return None


def test_opensky_provider_normalizes_successful_response():
    session = FakeSession(
        get_responses=[
            FakeResponse(
                status_code=200,
                json_payload={
                    "states": [
                        [
                            "abc123",
                            "TEST123 ",
                            "Australia",
                            0,
                            123456,
                            144.9,
                            -37.8,
                            1000,
                            False,
                            200,
                            180,
                            3,
                            None,
                            1100,
                            None,
                            False,
                            0,
                        ]
                    ]
                },
            )
        ]
    )
    provider = OpenSkyLiveFlightProvider(Settings(), session=session)

    flights = provider.get_flights_in_bounds(north=-37.7, south=-37.9, east=145.1, west=144.8)

    assert len(flights) == 1
    assert flights[0].icao24 == "abc123"
    assert flights[0].callsign == "TEST123"
    assert flights[0].origin_country == "Australia"


def test_opensky_provider_includes_historical_time_query_param():
    session = FakeSession(
        post_responses=[
            FakeResponse(
                status_code=200,
                json_payload={
                    "access_token": "token-123",
                    "expires_in": 1800,
                },
            )
        ],
        get_responses=[
            FakeResponse(
                status_code=200,
                json_payload={"states": []},
            )
        ]
    )
    provider = OpenSkyLiveFlightProvider(
        Settings(opensky_client_id="client-id", opensky_client_secret="client-secret"),
        session=session,
    )

    provider.get_flights_in_bounds(north=-37.7, south=-37.9, east=145.1, west=144.8, time_seconds=1_234)

    _, kwargs = session.get_calls[0]
    assert kwargs["params"]["time"] == 1_234


def test_opensky_provider_omits_historical_time_query_param_for_current_live_requests():
    session = FakeSession(
        get_responses=[
            FakeResponse(
                status_code=200,
                json_payload={"states": []},
            )
        ]
    )
    provider = OpenSkyLiveFlightProvider(Settings(), session=session)

    provider.get_flights_in_bounds(north=-37.7, south=-37.9, east=145.1, west=144.8)

    _, kwargs = session.get_calls[0]
    assert "time" not in kwargs["params"]


def test_opensky_provider_maps_rate_limit_error():
    provider = OpenSkyLiveFlightProvider(
        Settings(),
        session=FakeSession(get_responses=[FakeResponse(status_code=429, json_payload={})]),
    )

    with pytest.raises(LiveFlightProviderError) as exc_info:
        provider.get_flights_in_bounds(north=-37.7, south=-37.9, east=145.1, west=144.8)

    assert exc_info.value.code == "rate_limited"
    assert exc_info.value.provider == "opensky"


def test_opensky_provider_capabilities_require_credentials_for_history():
    provider_without_credentials = OpenSkyLiveFlightProvider(Settings())
    provider_with_credentials = OpenSkyLiveFlightProvider(
        Settings(opensky_client_id="client-id", opensky_client_secret="client-secret")
    )

    assert provider_without_credentials.capabilities.supports_history is False
    assert provider_without_credentials.capabilities.max_history_minutes == 0
    assert provider_with_credentials.capabilities.supports_history is True
    assert provider_with_credentials.capabilities.max_history_minutes == 60
    assert provider_with_credentials.capabilities.history_step_minutes == 1


def test_adsbx_provider_normalizes_successful_response():
    provider = ADSBxLiveFlightProvider(
        Settings(live_flight_provider="adsbx", adsbx_api_key="demo-key"),
        session=FakeSession(
            get_responses=[
                FakeResponse(
                    status_code=200,
                    json_payload={
                        "ac": [
                            {
                                "hex": "abc123",
                                "flight": "TEST123 ",
                                "lat": -37.8,
                                "lon": 144.9,
                                "alt_baro": 1000,
                                "gs": 220,
                                "track": 182,
                                "baro_rate": 5,
                                "seen_pos": 12,
                            }
                        ]
                    },
                )
            ]
        ),
    )

    flights = provider.get_flights_in_bounds(north=-37.7, south=-37.9, east=145.1, west=144.8)

    assert len(flights) == 1
    assert flights[0].icao24 == "abc123"
    assert flights[0].callsign == "TEST123"
    assert flights[0].origin_country is None


def test_adsbx_provider_maps_authentication_failure():
    provider = ADSBxLiveFlightProvider(
        Settings(live_flight_provider="adsbx", adsbx_api_key="demo-key"),
        session=FakeSession(get_responses=[FakeResponse(status_code=403, json_payload={})]),
    )

    with pytest.raises(LiveFlightProviderError) as exc_info:
        provider.get_flights_in_bounds(north=-37.7, south=-37.9, east=145.1, west=144.8)

    assert exc_info.value.code == "authentication_failed"
    assert exc_info.value.provider == "adsbx"


def test_adsbx_provider_does_not_support_history():
    provider = ADSBxLiveFlightProvider(
        Settings(live_flight_provider="adsbx", adsbx_api_key="demo-key"),
        session=FakeSession(),
    )

    assert provider.capabilities.provider == "adsbx"
    assert provider.capabilities.supports_history is False
    assert provider.capabilities.max_history_minutes == 0
    assert provider.capabilities.history_step_minutes == 1
