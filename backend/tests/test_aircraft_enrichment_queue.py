from __future__ import annotations

import asyncio
from pathlib import Path

from app.db import create_db_engine, create_session_maker
from app.models import AircraftRegistry, Base
from app.services.aircraft_enrichment_queue import AircraftEnrichmentQueue


class FakeEnrichmentService:
    def __init__(self, results=None, errors=None):
        self.results = results or {}
        self.errors = errors or set()
        self.calls = []
        self.warmed = False

    def warm_cache(self, allow_download: bool = False) -> None:
        self.warmed = True

    def enrich(self, db_session, icao24: str):
        self.calls.append(icao24)
        if icao24 in self.errors:
            raise RuntimeError("enrichment failed")
        payload = self.results.get(icao24)
        if payload is None:
            return None
        registry = AircraftRegistry(icao24=icao24, **payload)
        db_session.add(registry)
        db_session.flush()
        return registry


def make_session_maker(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'queue.db'}")
    Base.metadata.create_all(engine)
    return create_session_maker(engine)


def test_queue_persists_success_and_deduplicates(tmp_path: Path):
    session_maker = make_session_maker(tmp_path)
    service = FakeEnrichmentService(
        results={"abc123": {"manufacturer": "Airbus", "model": "A320-232", "type_code": "A320", "category": "L"}}
    )
    queue = AircraftEnrichmentQueue(session_maker, service)

    async def scenario():
        queue.start()
        queue.enqueue_many(["abc123", "abc123"])
        await queue.join()
        await queue.stop()

    asyncio.run(scenario())

    db_session = session_maker()
    try:
        stored = db_session.get(AircraftRegistry, "abc123")
        assert stored is not None
        assert stored.model == "A320-232"
        assert service.calls == ["abc123"]
    finally:
        db_session.close()


def test_queue_applies_failure_cooldown(tmp_path: Path):
    session_maker = make_session_maker(tmp_path)
    service = FakeEnrichmentService(errors={"abc123"})
    queue = AircraftEnrichmentQueue(session_maker, service, failure_cooldown_seconds=3600.0)

    async def scenario():
        queue.start()
        queue.enqueue_many(["abc123"])
        await queue.join()
        queue.enqueue_many(["abc123"])
        await queue.join()
        await queue.stop()

    asyncio.run(scenario())

    assert service.calls == ["abc123"]


def test_queue_clears_failure_cooldown_after_success(tmp_path: Path):
    session_maker = make_session_maker(tmp_path)
    service = FakeEnrichmentService()
    queue = AircraftEnrichmentQueue(session_maker, service, failure_cooldown_seconds=3600.0)

    async def scenario():
        queue.start()
        queue.enqueue_many(["abc123"])
        await queue.join()
        service.results["abc123"] = {"manufacturer": "Boeing", "model": "737-800", "type_code": "B738", "category": "M"}
        queue._last_failure_at_by_icao24["abc123"] = 0.0
        queue.enqueue_many(["abc123"])
        await queue.join()
        await queue.stop()

    asyncio.run(scenario())

    db_session = session_maker()
    try:
        stored = db_session.get(AircraftRegistry, "abc123")
        assert stored is not None
        assert stored.model == "737-800"
    finally:
        db_session.close()


def test_queue_warms_snapshot_in_background(tmp_path: Path):
    session_maker = make_session_maker(tmp_path)
    service = FakeEnrichmentService()
    queue = AircraftEnrichmentQueue(session_maker, service)

    asyncio.run(queue.warm_snapshot())

    assert service.warmed is True
