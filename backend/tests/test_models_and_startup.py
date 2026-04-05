from __future__ import annotations

import asyncio

from sqlalchemy import inspect, select, text

from app.db import create_db_engine
from app.main import create_app
from app.models import AircraftCategory, FlightLog, FlightLogPhoto


def test_startup_creates_expected_tables(app):
    async def run():
        async with app.router.lifespan_context(app):
            inspector = inspect(app.state.engine)
            assert {"flight_logs", "flight_log_photos", "aircraft_registry", "aircraft_types", "aircraft_categories"} <= set(
                inspector.get_table_names()
            )
            owner_uuid_columns = {column["name"] for column in inspector.get_columns("flight_logs")}
            assert "owner_uuid" in owner_uuid_columns
            assert "flight_time" in owner_uuid_columns
            session = app.state.session_maker()
            try:
                assert session.execute(
                    select(AircraftCategory).where(AircraftCategory.code == "L")
                ).scalar_one().label == "Light"
            finally:
                session.close()

    asyncio.run(run())


def test_startup_backfills_flight_time_for_existing_logs(settings):
    engine = create_db_engine(settings.database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE flight_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at DATETIME NOT NULL,
                    icao24 VARCHAR(6) NOT NULL,
                    callsign VARCHAR(16),
                    origin_country VARCHAR(64),
                    departure_airport VARCHAR(8),
                    arrival_airport VARCHAR(8),
                    aircraft_latitude NUMERIC(9, 6),
                    aircraft_longitude NUMERIC(9, 6),
                    altitude FLOAT,
                    velocity FLOAT,
                    heading FLOAT,
                    vertical_rate FLOAT,
                    owner_uuid VARCHAR(36),
                    logger_name VARCHAR(128),
                    logger_location VARCHAR(255),
                    logger_latitude NUMERIC(9, 6),
                    logger_longitude NUMERIC(9, 6),
                    note TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO flight_logs (created_at, icao24, note) VALUES (:created_at, :icao24, :note)"
            ),
            {
                "created_at": "2026-03-28 10:15:00+00:00",
                "icao24": "abc123",
                "note": "historical row",
            },
        )
    engine.dispose()

    app = create_app(settings)

    async def run():
        async with app.router.lifespan_context(app):
            inspector = inspect(app.state.engine)
            columns = {column["name"] for column in inspector.get_columns("flight_logs")}
            assert "flight_time" in columns
            session = app.state.session_maker()
            try:
                log = session.execute(select(FlightLog).where(FlightLog.icao24 == "abc123")).scalar_one()
                assert log.flight_time == log.created_at
            finally:
                session.close()

    asyncio.run(run())


def test_flight_log_photo_cascade(app):
    async def run():
        async with app.router.lifespan_context(app):
            session = app.state.session_maker()
            try:
                log = FlightLog(icao24="abc123")
                log.photos.append(FlightLogPhoto(file_path="flight_logs/1/test.jpg"))
                session.add(log)
                session.commit()
                photo_id = log.photos[0].id

                session.delete(log)
                session.commit()

                remaining = session.execute(
                    select(FlightLogPhoto).where(FlightLogPhoto.id == photo_id)
                ).scalar_one_or_none()
                assert remaining is None
            finally:
                session.close()

    asyncio.run(run())
