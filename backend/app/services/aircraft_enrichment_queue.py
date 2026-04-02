from __future__ import annotations

import asyncio
import queue
import threading
import time
from collections.abc import Iterable

from sqlalchemy.orm import Session, sessionmaker

from app.schemas import normalize_icao24
from app.services.aircraft_enrichment import AircraftEnrichmentService


class AircraftEnrichmentQueue:
    def __init__(
        self,
        session_maker: sessionmaker[Session],
        enrichment_service: AircraftEnrichmentService,
        failure_cooldown_seconds: float = 3600.0,
    ) -> None:
        self._session_maker = session_maker
        self._enrichment_service = enrichment_service
        self._failure_cooldown_seconds = failure_cooldown_seconds
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._queued: set[str] = set()
        self._inflight: set[str] = set()
        self._last_failure_at_by_icao24: dict[str, float] = {}
        self._worker_thread: threading.Thread | None = None
        self._state_lock = threading.Lock()

    def start(self) -> threading.Thread | None:
        if self._worker_thread is not None:
            return self._worker_thread
        self._worker_thread = threading.Thread(target=self._worker, name="aircraft-enrichment-worker", daemon=True)
        self._worker_thread.start()
        return self._worker_thread

    async def stop(self) -> None:
        if self._worker_thread is None:
            return
        self._queue.put_nowait(None)
        worker_thread = self._worker_thread
        self._worker_thread = None
        while worker_thread.is_alive():
            await asyncio.sleep(0.01)

    def enqueue_many(self, icao24s: Iterable[str]) -> None:
        now = time.monotonic()
        for raw_icao24 in icao24s:
            try:
                icao24 = normalize_icao24(raw_icao24)
            except ValueError:
                continue

            with self._state_lock:
                failed_at = self._last_failure_at_by_icao24.get(icao24)
                if failed_at is not None and now - failed_at < self._failure_cooldown_seconds:
                    continue
                if icao24 in self._queued or icao24 in self._inflight:
                    continue
                self._queued.add(icao24)
            self._queue.put_nowait(icao24)

    async def join(self) -> None:
        while self._queue.unfinished_tasks:
            await asyncio.sleep(0.01)

    async def warm_snapshot(self) -> None:
        self._enrichment_service.warm_cache(False)

    def _worker(self) -> None:
        while True:
            icao24 = self._queue.get()
            if icao24 is None:
                self._queue.task_done()
                break

            with self._state_lock:
                self._queued.discard(icao24)
                self._inflight.add(icao24)
            try:
                self._process_icao24(icao24)
            finally:
                with self._state_lock:
                    self._inflight.discard(icao24)
                self._queue.task_done()

    def _process_icao24(self, icao24: str) -> None:
        db_session = self._session_maker()
        try:
            registry = self._enrichment_service.enrich(db_session, icao24)
            if registry is None:
                db_session.rollback()
                with self._state_lock:
                    self._last_failure_at_by_icao24[icao24] = time.monotonic()
                return
            db_session.commit()
            with self._state_lock:
                self._last_failure_at_by_icao24.pop(icao24, None)
        except Exception:
            db_session.rollback()
            with self._state_lock:
                self._last_failure_at_by_icao24[icao24] = time.monotonic()
        finally:
            db_session.close()
