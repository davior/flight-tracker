from __future__ import annotations

import asyncio
import logging
from app.services.data_sync import DataSyncService

logger = logging.getLogger(__name__)


class DataRefreshScheduler:
    def __init__(
        self,
        sync_service: DataSyncService,
    ) -> None:
        self._sync_service = sync_service
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
        """Check all sources at startup; seed those that are absent or stale.

        If aircraft_registry is empty we force aircraft sources to seed immediately,
        bypassing the normal retry interval. This self-heals deployments where the
        initial seed failed (e.g. wrong URL, transient network error).
        """
        try:
            force_aircraft = await asyncio.to_thread(self._sync_service.aircraft_registry_is_empty)
            if force_aircraft:
                logger.warning(
                    "aircraft_registry is empty — forcing aircraft seed regardless of sync log"
                )
            await asyncio.to_thread(self._sync_service.seed_stale_sources, force_aircraft)
        except Exception:
            logger.exception("Data initial seed failed")

    async def _run(self) -> None:
        """Wake every hour and seed any sources that have become stale."""
        while True:
            await asyncio.sleep(3600)
            try:
                await asyncio.to_thread(self._sync_service.seed_stale_sources)
            except Exception:
                logger.exception("Unexpected error in data refresh scheduler")
