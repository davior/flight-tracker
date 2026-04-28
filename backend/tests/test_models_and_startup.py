from __future__ import annotations

import asyncio

from sqlalchemy import inspect, select

from app.config import Settings
from app.main import create_app
from app.models import AircraftCategory, FlightLog, FlightLogPhoto, User
from app.services.admin_seeder import seed_admin_user
from app.services.auth_service import verify_password


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


def test_flight_time_column_is_present_in_new_schema(app):
    """Test that flight_time column is created in fresh databases.

    This replaced the old manual migration test since we now use Alembic.
    """
    async def run():
        async with app.router.lifespan_context(app):
            inspector = inspect(app.state.engine)
            columns = {column["name"] for column in inspector.get_columns("flight_logs")}
            assert "flight_time" in columns

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


def test_seed_admin_user_updates_existing_account_credentials_and_flags(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'seed-admin.db'}",
        upload_dir=tmp_path / "uploads",
        runtime_dir=tmp_path / "runtime",
        jwt_secret_key="test-secret-key",
        admin_email="admin@example.com",
        admin_password="new-admin-password",
    )
    app = create_app(settings)

    async def run():
        async with app.router.lifespan_context(app):
            session = app.state.session_maker()
            try:
                admin = session.execute(select(User).where(User.email == "admin@example.com")).scalar_one()
                admin.password_hash = "stale-hash"
                admin.is_admin = False
                admin.is_active = False
                admin.is_verified = False
                admin.tutorial_seen = False
                session.commit()

                seed_admin_user(session, settings)
                session.refresh(admin)

                assert admin.is_admin is True
                assert admin.is_active is True
                assert admin.is_verified is True
                assert admin.tutorial_seen is True
                assert verify_password("new-admin-password", admin.password_hash)
            finally:
                session.close()

    asyncio.run(run())
