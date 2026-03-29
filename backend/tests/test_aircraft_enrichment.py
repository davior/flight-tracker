from __future__ import annotations

import gzip
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_maker
from app.models import AircraftRegistry, AircraftType, Base
from app.services.aircraft_enrichment import AircraftEnrichmentService


def write_snapshot(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle)


def make_session(settings) -> Session:
    engine = create_db_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_maker(engine)
    session = session_factory()
    return session


def test_enrichment_returns_cached_entry(settings):
    db_session = make_session(settings)
    db_session.add(
        AircraftRegistry(
            icao24="abc123",
            registration="VH-ABC",
            type_code="A320",
            manufacturer="Airbus",
            model="A320",
            category="L",
        )
    )
    db_session.commit()
    service = AircraftEnrichmentService(settings)

    result = service.enrich(db_session, "abc123")

    assert result is not None
    assert result.registration == "VH-ABC"


def test_enrichment_populates_from_snapshot(settings):
    db_session = make_session(settings)
    db_session.add(AircraftType(type_code="A320", manufacturer="Airbus", model="A320-232", category="L"))
    db_session.commit()
    write_snapshot(
        settings.adsbx_snapshot_path,
        [
            {
                "icao": "abc123",
                "reg": "VH-ABC",
                "icaotype": "A320",
                "manufacturer": "Airbus",
                "short_type": "L",
            }
        ],
    )
    service = AircraftEnrichmentService(settings)

    result = service.enrich(db_session, "abc123")

    assert result is not None
    assert result.registration == "VH-ABC"
    assert result.type_code == "A320"
    assert result.model == "A320-232"


def test_enrichment_handles_provider_failure_gracefully(settings):
    db_session = make_session(settings)
    service = AircraftEnrichmentService(settings)
    service.settings.adsbx_db_url = "https://127.0.0.1.invalid/basic-ac-db.json.gz"

    result = service.enrich(db_session, "abc123")

    assert result is None


def test_enrichment_returns_none_for_unknown_aircraft(settings):
    db_session = make_session(settings)
    write_snapshot(settings.adsbx_snapshot_path, [{"icao": "fff111", "reg": "VH-FFF"}])
    service = AircraftEnrichmentService(settings)

    result = service.enrich(db_session, "abc123")

    assert result is None
