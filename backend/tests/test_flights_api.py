from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.flights import get_nearby_flights
from app.db import create_db_engine, create_session_maker
from app.models import AircraftCategory, AircraftRegistry, Base
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

    def get_flights_in_bounds(self, north: float, south: float, east: float, west: float):
        self.calls.append({"north": north, "south": south, "east": east, "west": west})
        if self.error:
            raise self.error
        return self.flights


class FakeEnrichmentQueue:
    def __init__(self):
        self.calls = []

    def enqueue_many(self, icao24s):
        self.calls.append(list(icao24s))


def make_db_session() -> Session:
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_maker(engine)
    return session_factory()


def test_nearby_flights_accepts_bounds():
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
    db_session.add(
        AircraftCategory(
            code="L",
            label="Light",
            description="Small aircraft in the light wake turbulence category.",
        )
    )
    db_session.commit()

    response = get_nearby_flights(
        north=-37.7,
        south=-37.9,
        east=145.1,
        west=144.8,
        settings=settings,
        opensky_client=fake_client,
        enrichment_queue=FakeEnrichmentQueue(),
        db_session=db_session,
    )

    assert fake_client.calls == [{"north": -37.7, "south": -37.9, "east": 145.1, "west": 144.8}]
    assert response[0].icao24 == "abc123"
    assert response[0].display_type == "Airbus A320-232"
    assert response[0].category == "L"
    assert response[0].category_label == "Light"
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
        north=-37.7,
        south=-37.9,
        east=145.1,
        west=144.8,
        settings=settings,
        opensky_client=fake_client,
        enrichment_queue=FakeEnrichmentQueue(),
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
            north=-37.7,
            south=-37.9,
            east=145.1,
            west=144.8,
            settings=settings,
            opensky_client=FakeOpenSkyClient(error=OpenSkyError("rate limited")),
            enrichment_queue=FakeEnrichmentQueue(),
            db_session=db_session,
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == {"code": "opensky_unavailable", "message": "rate limited"}
    db_session.close()


def test_nearby_flights_rejects_invalid_bounds():
    settings = Settings()
    db_session = make_db_session()

    with pytest.raises(HTTPException) as exc_info:
        get_nearby_flights(
            north=-37.9,
            south=-37.7,
            east=145.1,
            west=144.8,
            settings=settings,
            opensky_client=FakeOpenSkyClient(),
            enrichment_queue=FakeEnrichmentQueue(),
            db_session=db_session,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "south must be less than north"
    db_session.close()


def test_nearby_flights_rejects_oversized_bounds():
    settings = Settings(max_nearby_radius_km=500)
    db_session = make_db_session()

    with pytest.raises(HTTPException) as exc_info:
        get_nearby_flights(
            north=85,
            south=-85,
            east=179,
            west=-179,
            settings=settings,
            opensky_client=FakeOpenSkyClient(),
            enrichment_queue=FakeEnrichmentQueue(),
            db_session=db_session,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "requested bounds exceed the maximum nearby radius of 500 km"
    db_session.close()


def test_nearby_flights_enqueues_missing_registry_for_background_enrichment():
    fake_client = FakeOpenSkyClient(
        flights=[
            FakeFlight(
                icao24="def456",
                callsign="TEST456",
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
    enrichment_queue = FakeEnrichmentQueue()
    settings = Settings()
    db_session = make_db_session()

    response = get_nearby_flights(
        north=-37.7,
        south=-37.9,
        east=145.1,
        west=144.8,
        settings=settings,
        opensky_client=fake_client,
        enrichment_queue=enrichment_queue,
        db_session=db_session,
    )

    assert enrichment_queue.calls == [["def456"]]
    assert response[0].display_type is None
    assert db_session.get(AircraftRegistry, "def456") is None
    db_session.close()


def test_nearby_flights_uses_known_registry_without_enqueuing_existing_aircraft():
    fake_client = FakeOpenSkyClient(
        flights=[
            FakeFlight(
                icao24="abc123",
                callsign="TEST789",
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
    enrichment_queue = FakeEnrichmentQueue()
    settings = Settings()
    db_session = make_db_session()
    db_session.add(
        AircraftCategory(
            code="L",
            label="Light",
            description="Small aircraft in the light wake turbulence category.",
        )
    )
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
        north=-37.7,
        south=-37.9,
        east=145.1,
        west=144.8,
        settings=settings,
        opensky_client=fake_client,
        enrichment_queue=enrichment_queue,
        db_session=db_session,
    )

    assert enrichment_queue.calls == []
    assert response[0].display_type == "Airbus A320-232"
    assert response[0].category == "L"
    db_session.close()


def test_nearby_flights_returns_unknown_aircraft_without_blocking():
    fake_client = FakeOpenSkyClient(
        flights=[
            FakeFlight(
                icao24="broken1",
                callsign="TESTBROKEN",
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
    enrichment_queue = FakeEnrichmentQueue()
    settings = Settings()
    db_session = make_db_session()

    response = get_nearby_flights(
        north=-37.7,
        south=-37.9,
        east=145.1,
        west=144.8,
        settings=settings,
        opensky_client=fake_client,
        enrichment_queue=enrichment_queue,
        db_session=db_session,
    )

    assert enrichment_queue.calls == [["broken1"]]
    assert response[0].display_type is None
    assert db_session.get(AircraftRegistry, "broken1") is None
    db_session.close()
