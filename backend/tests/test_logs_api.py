from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.api.logs import create_log, get_nearby_logs, get_photo
from app.db import create_db_engine, create_session_maker
from app.models import AircraftCategory, AircraftRegistry, Base, FlightLog, FlightLogPhoto, User
from PIL import Image, PngImagePlugin

from app.schemas import FlightLogCreate
from app.services.image_storage import ImageStorageService


class FakeLiveFlightProvider:
    class capabilities:
        supports_history = False


class FakeEnrichmentService:
    def __init__(self, registry=None):
        self.registry = registry
        self.calls = []

    def enrich(self, db_session, icao24: str):
        self.calls.append(icao24)
        return self.registry


def make_image_bytes(fmt: str, size: tuple[int, int] = (800, 600), with_text: bool = False) -> bytes:
    image = Image.new("RGB", size, color="navy")
    buffer = BytesIO()
    if fmt == "PNG":
        save_kwargs = {}
        if with_text:
            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text("Comment", "hello")
            save_kwargs["pnginfo"] = pnginfo
        image.save(buffer, format="PNG", **save_kwargs)
    else:
        image.save(buffer, format="JPEG")
    return buffer.getvalue()


class DummyUpload:
    def __init__(self, filename: str, content_type: str, payload: bytes):
        self.filename = filename
        self.content_type = content_type
        self._payload = payload

    async def read(self) -> bytes:
        return self._payload


def make_upload(filename: str, content_type: str, payload: bytes) -> DummyUpload:
    return DummyUpload(filename=filename, content_type=content_type, payload=payload)


def make_db_session(settings) -> Session:
    engine = create_db_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session_factory = create_session_maker(engine)
    return session_factory()


def make_test_user(db_session: Session, email: str = "test@example.com", username: str = "testuser") -> User:
    user = User(email=email, username=username, is_verified=True)
    db_session.add(user)
    db_session.flush()
    return user


def test_create_log_without_photos(settings):
    db_session = make_db_session(settings)
    user = make_test_user(db_session)
    payload = FlightLogCreate(icao24="ABC123", note="spotted")

    async def run():
        return await create_log(
            background_tasks=BackgroundTasks(),
            payload=payload,
            photos=None,
            current_user=user,
            db_session=db_session,
            enrichment_service=FakeEnrichmentService(),
            image_storage=ImageStorageService(settings.upload_dir),
            live_flight_provider=FakeLiveFlightProvider(),
            session_factory=None,
        )

    response = asyncio.run(run())

    assert response.icao24 == "abc123"
    assert response.note == "spotted"
    assert response.photos == []
    assert response.aircraft_registry is None
    assert response.flight_time == response.created_at
    assert response.owner_uuid is None
    assert response.owner_id == user.id
    assert response.owner_username == user.username

    db_session.close()


def test_create_log_with_single_photo_and_enrichment(settings):
    registry = SimpleNamespace(
        icao24="abc123",
        registration="VH-ABC",
        type_code="A320",
        manufacturer="Airbus",
        model="A320-232",
        category="L",
        first_seen="2026-03-29T00:00:00Z",
        last_updated="2026-03-29T00:00:00Z",
    )
    db_session = make_db_session(settings)
    user = make_test_user(db_session)
    payload = FlightLogCreate(icao24="ABC123")

    async def run():
        return await create_log(
            background_tasks=BackgroundTasks(),
            payload=payload,
            photos=[make_upload("photo.jpg", "image/jpeg", make_image_bytes("JPEG"))],
            current_user=user,
            db_session=db_session,
            enrichment_service=FakeEnrichmentService(registry=registry),
            image_storage=ImageStorageService(settings.upload_dir),
            live_flight_provider=FakeLiveFlightProvider(),
            session_factory=None,
        )

    response = asyncio.run(run())

    assert len(response.photos) == 1
    saved_path = Path(settings.upload_dir) / response.photos[0].file_path
    assert saved_path.exists()
    assert response.aircraft_registry.registration == "VH-ABC"
    assert response.photos[0].url == f"/photos/{response.photos[0].id}"
    assert response.flight_time == response.created_at
    assert response.owner_id == user.id
    assert response.owner_username == user.username

    db_session.close()


def test_create_log_with_three_photos(settings):
    files = [
        make_upload("1.jpg", "image/jpeg", make_image_bytes("JPEG")),
        make_upload("2.jpg", "image/jpeg", make_image_bytes("JPEG")),
        make_upload("3.png", "image/png", make_image_bytes("PNG")),
    ]
    db_session = make_db_session(settings)
    user = make_test_user(db_session)
    payload = FlightLogCreate(icao24="ABC123")

    async def run():
        return await create_log(
            background_tasks=BackgroundTasks(),
            payload=payload,
            photos=files,
            current_user=user,
            db_session=db_session,
            enrichment_service=FakeEnrichmentService(),
            image_storage=ImageStorageService(settings.upload_dir),
            live_flight_provider=FakeLiveFlightProvider(),
            session_factory=None,
        )

    response = asyncio.run(run())

    assert len(response.photos) == 3

    db_session.close()


def test_create_log_rejects_more_than_three_photos(settings):
    files = [
        make_upload(f"{index}.jpg", "image/jpeg", make_image_bytes("JPEG"))
        for index in range(4)
    ]
    db_session = make_db_session(settings)
    user = make_test_user(db_session)
    payload = FlightLogCreate(icao24="ABC123")

    async def run():
        return await create_log(
            background_tasks=BackgroundTasks(),
            payload=payload,
            photos=files,
            current_user=user,
            db_session=db_session,
            enrichment_service=FakeEnrichmentService(),
            image_storage=ImageStorageService(settings.upload_dir),
            live_flight_provider=FakeLiveFlightProvider(),
            session_factory=None,
        )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(run())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "A maximum of 3 photos is allowed"

    db_session.close()


def test_create_log_rejects_unsupported_image(settings):
    db_session = make_db_session(settings)
    user = make_test_user(db_session)
    payload = FlightLogCreate(icao24="ABC123")

    async def run():
        return await create_log(
            background_tasks=BackgroundTasks(),
            payload=payload,
            photos=[make_upload("note.txt", "text/plain", b"not-an-image")],
            current_user=user,
            db_session=db_session,
            enrichment_service=FakeEnrichmentService(),
            image_storage=ImageStorageService(settings.upload_dir),
            live_flight_provider=FakeLiveFlightProvider(),
            session_factory=None,
        )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(run())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Only JPEG and PNG uploads are supported"

    db_session.close()


def test_create_log_rejects_bad_icao24():
    with pytest.raises(ValidationError) as exc_info:
        FlightLogCreate(icao24="BAD")

    assert "icao24" in str(exc_info.value)


def test_create_log_persists_provided_flight_time(settings):
    db_session = make_db_session(settings)
    user = make_test_user(db_session)
    flight_time = datetime(2026, 3, 28, 8, 45, tzinfo=timezone.utc)
    payload = FlightLogCreate(icao24="ABC123", flight_time=flight_time, note="historical")

    async def run():
        return await create_log(
            background_tasks=BackgroundTasks(),
            payload=payload,
            photos=None,
            current_user=user,
            db_session=db_session,
            enrichment_service=FakeEnrichmentService(),
            image_storage=ImageStorageService(settings.upload_dir),
            live_flight_provider=FakeLiveFlightProvider(),
            session_factory=None,
        )

    response = asyncio.run(run())

    assert response.flight_time.replace(tzinfo=timezone.utc) == flight_time
    persisted = db_session.get(FlightLog, response.id)
    assert persisted is not None
    assert persisted.flight_time.replace(tzinfo=timezone.utc) == flight_time
    db_session.close()


def test_get_nearby_logs_returns_distance_and_owner(settings):
    db_session = make_db_session(settings)
    user = make_test_user(db_session)
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
    log = FlightLog(
        icao24="abc123",
        callsign="TEST123",
        note="low pass",
        owner_id=user.id,
        aircraft_latitude=-37.810000,
        aircraft_longitude=144.965000,
    )
    db_session.add(log)
    db_session.flush()
    log.photos.append(FlightLogPhoto(file_path="flight_logs/1/test.jpg"))
    db_session.commit()

    results = get_nearby_logs(
        north=-37.7,
        south=-37.9,
        east=145.1,
        west=144.8,
        time_window_days=1.0,
        current_user=user,
        settings=settings,
        db_session=db_session,
    )

    assert len(results) == 1
    assert results[0].is_owner is True
    assert results[0].owner_id == user.id
    assert results[0].owner_username == user.username
    assert results[0].display_type == "Airbus A320-232"
    assert results[0].category == "L"
    assert results[0].category_label == "Light"
    assert results[0].photos[0].url == f"/photos/{results[0].photos[0].id}"
    assert results[0].distance_km > 0
    assert results[0].flight_time == log.flight_time

    db_session.close()


def test_get_nearby_logs_excludes_points_outside_bounds(settings):
    db_session = make_db_session(settings)
    db_session.add(
        FlightLog(
            icao24="abc123",
            aircraft_latitude=-37.5,
            aircraft_longitude=145.4,
        )
    )
    db_session.commit()

    results = get_nearby_logs(
        north=-37.7,
        south=-37.9,
        east=145.1,
        west=144.8,
        time_window_days=1.0,
        current_user=None,
        settings=settings,
        db_session=db_session,
    )

    assert results == []
    db_session.close()


def test_get_nearby_logs_filters_by_flight_time(settings):
    db_session = make_db_session(settings)
    now = datetime.now(timezone.utc)
    db_session.add(
        FlightLog(
            icao24="recent1",
            created_at=now,
            flight_time=now - timedelta(hours=2),
            aircraft_latitude=-37.810000,
            aircraft_longitude=144.965000,
        )
    )
    db_session.add(
        FlightLog(
            icao24="recent2",
            created_at=now - timedelta(days=2),
            flight_time=now - timedelta(hours=1),
            aircraft_latitude=-37.810000,
            aircraft_longitude=144.965000,
        )
    )
    db_session.commit()

    results = get_nearby_logs(
        north=-37.7,
        south=-37.9,
        east=145.1,
        west=144.8,
        time_window_days=0.5,
        current_user=None,
        settings=settings,
        db_session=db_session,
    )

    assert [item.icao24 for item in results] == ["recent2", "recent1"]
    db_session.close()


def test_get_nearby_logs_rejects_invalid_bounds(settings):
    db_session = make_db_session(settings)

    with pytest.raises(HTTPException) as exc_info:
        get_nearby_logs(
            north=-37.9,
            south=-37.7,
            east=145.1,
            west=144.8,
            time_window_days=1.0,
            current_user=None,
            settings=settings,
            db_session=db_session,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "south must be less than north"
    db_session.close()


@pytest.mark.parametrize("time_window_days", [0.5, 1.0, 1.5, 28.0])
def test_get_nearby_logs_accepts_numeric_day_windows(settings, time_window_days: float):
    db_session = make_db_session(settings)

    log = FlightLog(
        icao24="abc123",
        aircraft_latitude=-37.810000,
        aircraft_longitude=144.965000,
    )
    db_session.add(log)
    db_session.commit()

    results = get_nearby_logs(
        north=-37.7,
        south=-37.9,
        east=145.1,
        west=144.8,
        time_window_days=time_window_days,
        current_user=None,
        settings=settings,
        db_session=db_session,
    )

    assert len(results) == 1
    db_session.close()


@pytest.mark.parametrize(
    ("time_window_days", "message"),
    [
        (0.25, "time_window_days must be between 0.5 and 28"),
        (0.75, "time_window_days must be in 0.5 day increments"),
        (29.0, "time_window_days must be between 0.5 and 28"),
        (-1.0, "time_window_days must be between 0.5 and 28"),
    ],
)
def test_get_nearby_logs_rejects_invalid_numeric_day_windows(settings, time_window_days: float, message: str):
    db_session = make_db_session(settings)

    with pytest.raises(HTTPException) as exc_info:
        get_nearby_logs(
            north=-37.7,
            south=-37.9,
            east=145.1,
            west=144.8,
            time_window_days=time_window_days,
            current_user=None,
            settings=settings,
            db_session=db_session,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == message
    db_session.close()


def test_get_photo_returns_file_response(settings):
    db_session = make_db_session(settings)
    target_dir = settings.upload_dir / "flight_logs" / "1"
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / "photo.jpg"
    file_path.write_bytes(make_image_bytes("JPEG"))
    photo = FlightLogPhoto(flight_log_id=1, file_path="flight_logs/1/photo.jpg")
    log = FlightLog(id=1, icao24="abc123")
    db_session.add(log)
    db_session.flush()
    db_session.add(photo)
    db_session.commit()

    response = get_photo(photo.id, db_session=db_session, settings=settings)

    assert Path(response.path) == file_path
    assert response.media_type == "image/jpeg"

    db_session.close()
