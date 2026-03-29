from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.flights import router as flights_router
from app.api.logs import photo_router, router as logs_router
from app.config import Settings, get_settings
from app.db import Base, create_db_engine, create_session_maker, wait_for_database
from app.services.aircraft_enrichment import AircraftEnrichmentService
from app.services.image_storage import ImageStorageService
from app.services.opensky import OpenSkyClient


def create_app(settings_override: Settings | None = None) -> FastAPI:
    settings = settings_override or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.ensure_directories()
        engine = create_db_engine(settings.database_url)
        session_maker = create_session_maker(engine)

        app.state.settings = settings
        app.state.engine = engine
        app.state.session_maker = session_maker
        app.state.opensky_client = OpenSkyClient(settings)
        app.state.enrichment_service = AircraftEnrichmentService(settings)
        app.state.image_storage = ImageStorageService(settings.upload_dir)

        await wait_for_database(
            engine,
            max_attempts=settings.db_startup_max_attempts,
            retry_delay_seconds=settings.db_startup_retry_delay_seconds,
        )
        Base.metadata.create_all(bind=engine)

        try:
            yield
        finally:
            app.state.opensky_client.close()
            app.state.enrichment_service.close()
            engine.dispose()

    application = FastAPI(title="Flight Logger API", lifespan=lifespan)
    application.include_router(flights_router)
    application.include_router(logs_router)
    application.include_router(photo_router)
    return application


app = create_app()
