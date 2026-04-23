from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, sessionmaker

from app.models import DataSyncLog

if TYPE_CHECKING:
    from app.services.data_seeder import DataSeeder

logger = logging.getLogger(__name__)


class DataRefreshScheduler:
    def __init__(
        self,
        seeder: DataSeeder,
        session_maker: sessionmaker[Session],
        aircraft_refresh_interval_hours: int = 168,
        airport_refresh_interval_hours: int = 720,
    ) -> None:
        self._seeder = seeder
        self._session_maker = session_maker
        self._aircraft_interval = timedelta(hours=aircraft_refresh_interval_hours)
        self._airport_interval = timedelta(hours=airport_refresh_interval_hours)
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="data-refresh-scheduler")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def run_initial_seed(self) -> None:
        """Check all sources at startup; seed those that are absent or stale."""
        await asyncio.to_thread(self._seed_stale_sources)

    async def _run(self) -> None:
        """Wake every hour and seed any sources that have become stale."""
        while True:
            await asyncio.sleep(3600)
            try:
                await asyncio.to_thread(self._seed_stale_sources)
            except Exception:
                logger.exception("Unexpected error in data refresh scheduler")

    def _seed_stale_sources(self) -> None:
        from app.services.data_seeder import (
            SOURCE_FAA_AIRCRAFT,
            SOURCE_OPENSKY_AIRCRAFT,
            SOURCE_OPENSKY_ROUTES,
            SOURCE_OURAIRPORTS,
        )
        self._maybe_seed(SOURCE_OPENSKY_AIRCRAFT, self._aircraft_interval, self._seeder.seed_opensky_aircraft)
        self._maybe_seed(SOURCE_FAA_AIRCRAFT, self._aircraft_interval, self._seeder.seed_faa_aircraft)
        self._maybe_seed(SOURCE_OURAIRPORTS, self._airport_interval, self._seeder.seed_airports)
        self._maybe_seed(SOURCE_OPENSKY_ROUTES, self._aircraft_interval, self._seeder.seed_routes)

    def _maybe_seed(
        self,
        source: str,
        max_age: timedelta,
        seed_fn: Callable[[], int],
    ) -> None:
        session = self._session_maker()
        try:
            record = session.get(DataSyncLog, source)
            if record is not None and record.last_synced_at is not None:
                last_synced = record.last_synced_at
                if last_synced.tzinfo is None:
                    last_synced = last_synced.replace(tzinfo=timezone.utc)
                age = datetime.now(timezone.utc) - last_synced
                if age < max_age:
                    return
        finally:
            session.close()

        logger.info("Seeding data source: %s", source)
        try:
            count = seed_fn()
            logger.info("Seeded %s: %d rows", source, count)
        except Exception:
            logger.exception("Failed to seed data source: %s", source)
