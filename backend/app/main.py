from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.logging_config import setup_logging
from app.api.auth import router as auth_router
from app.api.flights import router as flights_router
from app.api.logs import photo_router, router as logs_router
from app.config import Settings, get_settings
from app.db import Base, create_db_engine, create_session_maker, wait_for_database
from app.migrations import run_migrations
from app.services.aircraft_enrichment import AircraftEnrichmentService
from app.services.aircraft_categories import seed_aircraft_categories
from app.services.aircraft_enrichment_queue import AircraftEnrichmentQueue
from app.services.image_storage import ImageStorageService
from app.services.live_flight_provider_factory import create_live_flight_provider


def create_app(settings_override: Settings | None = None) -> FastAPI:
    settings = settings_override or get_settings()
    setup_logging(
        level=settings.log_level,
        log_file=settings.log_file,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.ensure_directories()
        engine = create_db_engine(settings.database_url)
        session_maker = create_session_maker(engine)

        app.state.settings = settings
        app.state.engine = engine
        app.state.session_maker = session_maker
        app.state.live_flight_provider = create_live_flight_provider(settings)
        app.state.enrichment_service = AircraftEnrichmentService(settings)
        app.state.enrichment_queue = AircraftEnrichmentQueue(session_maker, app.state.enrichment_service)
        app.state.image_storage = ImageStorageService(settings.upload_dir)

        await wait_for_database(
            engine,
            max_attempts=settings.db_startup_max_attempts,
            retry_delay_seconds=settings.db_startup_retry_delay_seconds,
        )

        # Run database migrations (or create_all for in-memory test databases)
        run_migrations(engine)

        session = session_maker()
        try:
            seed_aircraft_categories(session)
            session.commit()
        finally:
            session.close()

        try:
            app.state.enrichment_queue.start()
            app.state.enrichment_warmup_task = asyncio.create_task(
                app.state.enrichment_queue.warm_snapshot(),
                name="aircraft-enrichment-warmup",
            )
            yield
        finally:
            if app.state.enrichment_warmup_task is not None:
                app.state.enrichment_warmup_task.cancel()
                try:
                    await app.state.enrichment_warmup_task
                except asyncio.CancelledError:
                    pass
            await app.state.enrichment_queue.stop()
            app.state.live_flight_provider.close()
            app.state.enrichment_service.close()
            engine.dispose()

    application = FastAPI(title="Flight Logger API", lifespan=lifespan)
    application.include_router(auth_router)
    application.include_router(flights_router)
    application.include_router(logs_router)
    application.include_router(photo_router)
    return application


app = create_app()
