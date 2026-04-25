from __future__ import annotations

import io
import socket
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import DataError as SQLAlchemyDataError

from app.db import create_db_engine, create_session_maker
from app.models import AircraftRegistry, Base, DataSyncLog
from app.services.data_seeder import SOURCE_FAA_AIRCRAFT, SOURCE_OPENSKY_AIRCRAFT, DataSeeder
from app.services.data_sync import DataSyncService
from sync_data import run_cli


def make_service(settings):
    if not settings.opensky_aircraft_db_url:
        settings.opensky_aircraft_db_url = "https://example.invalid/aircraft.csv"
    engine = create_db_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session_maker = create_session_maker(engine)
    seeder = DataSeeder(settings, session_maker)
    service = DataSyncService(settings, seeder, session_maker)
    return engine, session_maker, seeder, service


def test_opensky_seed_retries_transient_dns_failure_and_succeeds(settings, monkeypatch):
    settings.opensky_seed_retry_attempts = 2
    settings.opensky_seed_retry_base_delay_seconds = 0.0
    engine, session_maker, seeder, _ = make_service(settings)
    calls = {"count": 0}

    def fake_stream_rows(_url):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ConnectionError("lookup failed") from socket.gaierror(
                -3, "Temporary failure in name resolution"
            )
        return iter([
            {
                "icao24": "abc123",
                "registration": "VH-ABC",
                "manufacturername": "Airbus",
                "model": "A320",
                "typecode": "A320",
                "categoryDescription": "L",
                "operator": "Demo Air",
                "operatoricao": "DMO",
                "operatoriata": "D1",
                "operatorcallsign": "DEMO",
                "owner": "Owner",
                "serialnumber": "123",
                "built": "2015",
                "engines": "2",
                "icaoaircrafttype": "L2J",
            }
        ])

    monkeypatch.setattr(seeder, "_stream_csv_rows", fake_stream_rows)

    try:
        assert seeder.seed_opensky_aircraft() == 1
        assert calls["count"] == 2

        session = session_maker()
        try:
            record = session.get(AircraftRegistry, "abc123")
            assert record is not None
            assert record.manufacturer == "Airbus"
            sync = session.get(DataSyncLog, SOURCE_OPENSKY_AIRCRAFT)
            assert sync is not None
            assert sync.last_sync_status == "ok"
            assert sync.row_count == 1
        finally:
            session.close()
    finally:
        seeder.close()
        engine.dispose()


def test_opensky_seed_marks_error_with_useful_message(settings, monkeypatch):
    settings.opensky_seed_retry_attempts = 1
    engine, session_maker, seeder, _ = make_service(settings)

    def fake_stream_rows(_url):
        raise ValueError("bad csv header")

    monkeypatch.setattr(seeder, "_stream_csv_rows", fake_stream_rows)

    try:
        with pytest.raises(ValueError):
            seeder.seed_opensky_aircraft()

        session = session_maker()
        try:
            sync = session.get(DataSyncLog, SOURCE_OPENSKY_AIRCRAFT)
            assert sync is not None
            assert sync.last_sync_status == "error"
            assert sync.last_sync_error is not None
            assert "parse_error:" in sync.last_sync_error
            assert settings.opensky_aircraft_db_url in sync.last_sync_error
        finally:
            session.close()
    finally:
        seeder.close()
        engine.dispose()


def test_opensky_seed_drops_overlong_unknown_category_and_still_succeeds(settings, monkeypatch):
    engine, session_maker, seeder, _ = make_service(settings)

    monkeypatch.setattr(
        seeder,
        "_stream_csv_rows",
        lambda _url: iter([
            {
                "icao24": "feed01",
                "registration": "VH-FED",
                "manufacturername": "Boeing",
                "model": "737",
                "typecode": "B737",
                "categoryDescription": "Large (75000 to 300000 lbs)",
                "operator": "",
                "operatoricao": "",
                "operatoriata": "",
                "operatorcallsign": "",
                "owner": "",
                "serialnumber": "",
                "built": "",
                "engines": "",
                "icaoaircrafttype": "L2J",
            }
        ]),
    )

    try:
        assert seeder.seed_opensky_aircraft() == 1
        session = session_maker()
        try:
            registry = session.get(AircraftRegistry, "feed01")
            assert registry is not None
            assert registry.category is None
            sync = session.get(DataSyncLog, SOURCE_OPENSKY_AIRCRAFT)
            assert sync is not None
            assert sync.last_sync_status == "ok"
        finally:
            session.close()
    finally:
        seeder.close()
        engine.dispose()


def test_sync_error_message_is_compact_for_sqlalchemy_data_errors(settings):
    engine, session_maker, seeder, _ = make_service(settings)
    try:
        original = Exception("value too long")
        error = SQLAlchemyDataError(
            "INSERT INTO aircraft_registry VALUES (...)",
            {"category": "LARGE_(75000_TO_300000_LBS)"},
            original,
        )
        message = seeder._format_sync_error("db_error", settings.opensky_aircraft_db_url, error)  # noqa: SLF001
        assert "db_error:" in message
        assert "value too long" in message
        assert "INSERT INTO aircraft_registry" not in message
        assert len(message) < 500
    finally:
        seeder.close()
        engine.dispose()


def test_truncate_string_caps_overlong_opensky_fields(settings):
    engine, _session_maker, seeder, _ = make_service(settings)
    try:
        assert seeder._truncate_string("engines", "X" * 200) == "X" * 128  # noqa: SLF001
        assert seeder._truncate_string("manufacturer", "Y" * 200) == "Y" * 128  # noqa: SLF001
        assert seeder._truncate_string("registration", "Z" * 40) == "Z" * 32  # noqa: SLF001
    finally:
        seeder.close()
        engine.dispose()


def test_sync_service_uses_short_failed_retry_interval(settings, monkeypatch):
    settings.failed_source_retry_hours = 2
    settings.aircraft_refresh_interval_hours = 168
    engine = create_db_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session_maker = create_session_maker(engine)
    seeder = DataSeeder(settings, session_maker)
    called: list[str] = []

    monkeypatch.setattr(seeder, "seed_opensky_aircraft", lambda: called.append("opensky") or 1)
    monkeypatch.setattr(seeder, "seed_faa_aircraft", lambda: called.append("faa") or 0)
    monkeypatch.setattr(seeder, "seed_airports", lambda: called.append("airports") or 0)
    monkeypatch.setattr(seeder, "seed_routes", lambda: called.append("routes") or 0)
    monkeypatch.setattr(seeder, "seed_openflights_routes", lambda: called.append("openflights") or 0)
    service = DataSyncService(settings, seeder, session_maker)

    session = session_maker()
    now = datetime.now(timezone.utc)
    try:
        session.add(
            DataSyncLog(
                source=SOURCE_OPENSKY_AIRCRAFT,
                last_synced_at=now - timedelta(hours=3),
                last_sync_status="error",
                row_count=None,
            )
        )
        session.add(
            DataSyncLog(
                source=SOURCE_FAA_AIRCRAFT,
                last_synced_at=now - timedelta(minutes=30),
                last_sync_status="ok",
                row_count=1,
            )
        )
        session.add(
            DataSyncLog(
                source="ourairports",
                last_synced_at=now - timedelta(minutes=30),
                last_sync_status="ok",
                row_count=1,
            )
        )
        session.add(
            DataSyncLog(
                source="opensky_routes",
                last_synced_at=now - timedelta(minutes=30),
                last_sync_status="ok",
                row_count=1,
            )
        )
        session.add(
            DataSyncLog(
                source="openflights_routes",
                last_synced_at=now - timedelta(minutes=30),
                last_sync_status="ok",
                row_count=1,
            )
        )
        session.commit()
    finally:
        session.close()

    try:
        service.seed_stale_sources()
        assert called == ["opensky"]
    finally:
        seeder.close()
        engine.dispose()


def test_manual_sync_cli_uses_shared_service():
    class FakeRecord:
        source = "opensky_aircraft"
        last_sync_status = "ok"
        row_count = 42
        last_synced_at = datetime(2026, 4, 25, 0, 0, tzinfo=timezone.utc)

    class FakeSyncService:
        def __init__(self):
            self.seeded: list[str] = []

        def seed_source(self, source: str) -> int:
            self.seeded.append(source)
            if source == "broken":
                raise RuntimeError("boom")
            return 42

        def list_sync_statuses(self):
            return [FakeRecord()]

    sync_service = FakeSyncService()
    stdout = io.StringIO()
    stderr = io.StringIO()

    assert run_cli(["opensky_aircraft"], sync_service=sync_service, stdout=stdout, stderr=stderr) == 0
    assert sync_service.seeded == ["opensky_aircraft"]
    assert "Synced opensky_aircraft: 42 rows" in stdout.getvalue()

    stdout = io.StringIO()
    assert run_cli(["--status"], sync_service=sync_service, stdout=stdout, stderr=stderr) == 0
    assert "opensky_aircraft\tok\t42" in stdout.getvalue()

    stderr = io.StringIO()
    assert run_cli(["broken"], sync_service=sync_service, stdout=stdout, stderr=stderr) == 1
    assert "Sync failed for broken: boom" in stderr.getvalue()


def test_opensky_seed_populates_registry_and_sync_status(settings, monkeypatch):
    engine, session_maker, seeder, _ = make_service(settings)

    monkeypatch.setattr(
        seeder,
        "_stream_csv_rows",
        lambda _url: iter([
            {
                "icao24": "def456",
                "registration": "VH-DEF",
                "manufacturername": "Boeing",
                "model": "737-8",
                "typecode": "B738",
                "categoryDescription": "M",
                "operator": "Demo Jet",
                "operatoricao": "DJT",
                "operatoriata": "D2",
                "operatorcallsign": "JET",
                "owner": "Owner 2",
                "serialnumber": "456",
                "built": "2018",
                "engines": "2",
                "icaoaircrafttype": "L2J",
            }
        ]),
    )

    try:
        seeder.seed_opensky_aircraft()
        session = session_maker()
        try:
            registry = session.get(AircraftRegistry, "def456")
            assert registry is not None
            assert registry.manufacturer == "Boeing"
            assert registry.type_code == "B738"
            sync = session.get(DataSyncLog, SOURCE_OPENSKY_AIRCRAFT)
            assert sync is not None
            assert sync.last_sync_status == "ok"
            assert sync.row_count == 1
        finally:
            session.close()
    finally:
        seeder.close()
        engine.dispose()


def test_faa_upsert_preserves_existing_rich_metadata(settings):
    engine, session_maker, seeder, _ = make_service(settings)
    session = session_maker()
    try:
        session.add(
            AircraftRegistry(
                icao24="abc123",
                manufacturer="Airbus",
                model="A320",
                registration=None,
            )
        )
        session.commit()
    finally:
        session.close()

    try:
        seeder._upsert_aircraft_batch_faa(  # noqa: SLF001 - direct regression check for sparse FAA upsert
            [
                {
                    "icao24": "abc123",
                    "registration": "N123AB",
                    "first_seen": datetime.now(timezone.utc),
                    "last_updated": datetime.now(timezone.utc),
                }
            ]
        )
        session = session_maker()
        try:
            registry = session.get(AircraftRegistry, "abc123")
            assert registry is not None
            assert registry.registration == "N123AB"
            assert registry.manufacturer == "Airbus"
            assert registry.model == "A320"
        finally:
            session.close()
    finally:
        seeder.close()
        engine.dispose()
