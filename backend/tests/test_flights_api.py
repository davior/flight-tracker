from __future__ import annotations

import inspect
from dataclasses import dataclass

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.flights import get_nearby_flights
from app.db import create_db_engine, create_session_maker
from app.models import AircraftRegistry, Base
from app.config import Settings
from app.services.opensky import OpenSkyError


@dataclass
class FakeFlight:
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


class FakeOpenSkyClient:
    def __init__(self, flights=None, error: Exception | None = None):
        self.flights = flights or []
        self.error = error
        self.calls = []

    def get_nearby_flights(self, lat: float, lon: float, radius_km: float):
        self.calls.append({"lat": lat, "lon": lon, "radius_km": radius_km})
        if self.error:
            raise self.error
        return self.flights


def make_db_session() -> Session:
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_maker(engine)
    return session_factory()


def test_nearby_flights_uses_default_radius():
    radius_default = inspect.signature(get_nearby_flights).parameters["radius_km"].default
    assert radius_default.default == 20.0


def test_nearby_flights_accepts_custom_radius():
    fake_client = FakeOpenSkyClient(
        flights=[
            FakeFlight(
                icao24="abc123",
                callsign="TEST123",
                origin_country="Australia",
                latitude=-37.8,
                longitude=144.9,
                altitude=10000.0,
                velocity=200.0,
                heading=180.0,
                vertical_rate=0.0,
                last_contact=123456,
                distance_km=5.2,
            )
        ]
    )
    settings = Settings()
    db_session = make_db_session()
    db_session.add(
        AircraftRegistry(
            icao24="abc123",
            type_code="A320",
            manufacturer="Airbus",
            model="A320-232",
            category="L",
        )
    )
    db_session.commit()

    response = get_nearby_flights(
        lat=-37.81,
        lon=144.96,
        radius_km=50.0,
        settings=settings,
        opensky_client=fake_client,
        db_session=db_session,
    )

    assert fake_client.calls == [{"lat": -37.81, "lon": 144.96, "radius_km": 50.0}]
    assert response[0].icao24 == "abc123"
    assert response[0].display_type == "Airbus A320-232"
    db_session.close()


def test_nearby_flights_returns_distance_filtered_results():
    fake_client = FakeOpenSkyClient(
        flights=[
            FakeFlight(
                icao24="near01",
                callsign=None,
                origin_country="Australia",
                latitude=-37.81,
                longitude=144.97,
                altitude=None,
                velocity=None,
                heading=None,
                vertical_rate=None,
                last_contact=None,
                distance_km=3.0,
            )
        ]
    )
    settings = Settings()
    db_session = make_db_session()

    response = get_nearby_flights(
        lat=-37.81,
        lon=144.96,
        radius_km=20.0,
        settings=settings,
        opensky_client=fake_client,
        db_session=db_session,
    )

    assert len(response) == 1
    assert response[0].distance_km == 3.0
    db_session.close()


def test_nearby_flights_returns_502_when_opensky_fails():
    settings = Settings()
    db_session = make_db_session()

    with pytest.raises(HTTPException) as exc_info:
        get_nearby_flights(
            lat=-37.81,
            lon=144.96,
            radius_km=20.0,
            settings=settings,
            opensky_client=FakeOpenSkyClient(error=OpenSkyError("rate limited")),
            db_session=db_session,
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == {"code": "opensky_unavailable", "message": "rate limited"}
    db_session.close()
