from __future__ import annotations

import asyncio

from sqlalchemy import inspect, select

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
            session = app.state.session_maker()
            try:
                assert session.execute(
                    select(AircraftCategory).where(AircraftCategory.code == "L")
                ).scalar_one().label == "Light"
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
