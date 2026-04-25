from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models import AircraftRegistry, DataSyncLog
from app.services.data_seeder import (
    SOURCE_FAA_AIRCRAFT,
    SOURCE_OPENFLIGHTS_ROUTES,
    SOURCE_OPENSKY_AIRCRAFT,
    SOURCE_OPENSKY_ROUTES,
    SOURCE_OURAIRPORTS,
    DataSeeder,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DataSourceSpec:
    source: str
    max_age: timedelta
    seed_fn: Callable[[], int]
    is_aircraft_source: bool = False


class DataSyncService:
    def __init__(
        self,
        settings: Settings,
        seeder: DataSeeder,
        session_maker: sessionmaker[Session],
    ) -> None:
        self._settings = settings
        self._seeder = seeder
        self._session_maker = session_maker
        self._failed_retry = timedelta(hours=settings.failed_source_retry_hours)
        self._sources: tuple[DataSourceSpec, ...] = (
            DataSourceSpec(
                source=SOURCE_OPENSKY_AIRCRAFT,
                max_age=timedelta(hours=settings.aircraft_refresh_interval_hours),
                seed_fn=seeder.seed_opensky_aircraft,
                is_aircraft_source=True,
            ),
            DataSourceSpec(
                source=SOURCE_FAA_AIRCRAFT,
                max_age=timedelta(hours=settings.aircraft_refresh_interval_hours),
                seed_fn=seeder.seed_faa_aircraft,
                is_aircraft_source=True,
            ),
            DataSourceSpec(
                source=SOURCE_OURAIRPORTS,
                max_age=timedelta(hours=settings.airport_refresh_interval_hours),
                seed_fn=seeder.seed_airports,
            ),
            DataSourceSpec(
                source=SOURCE_OPENSKY_ROUTES,
                max_age=timedelta(hours=settings.aircraft_refresh_interval_hours),
                seed_fn=seeder.seed_routes,
            ),
            DataSourceSpec(
                source=SOURCE_OPENFLIGHTS_ROUTES,
                max_age=timedelta(hours=settings.aircraft_refresh_interval_hours),
                seed_fn=seeder.seed_openflights_routes,
            ),
        )
        self._sources_by_name = {spec.source: spec for spec in self._sources}

    def available_sources(self) -> tuple[str, ...]:
        return tuple(self._sources_by_name)

    def seed_source(self, source: str) -> int:
        spec = self._sources_by_name.get(source)
        if spec is None:
            available = ", ".join(self.available_sources())
            raise ValueError(f"Unknown data source '{source}'. Available sources: {available}")
        logger.info("Manual sync triggered for source: %s", source)
        return spec.seed_fn()

    def list_sync_statuses(self) -> list[DataSyncLog]:
        session = self._session_maker()
        try:
            records = session.execute(
                select(DataSyncLog).order_by(DataSyncLog.source.asc())
            ).scalars()
            return list(records)
        finally:
            session.close()

    def aircraft_registry_is_empty(self) -> bool:
        """Return True if the registry has no rows with real enrichment data."""
        session = self._session_maker()
        try:
            count = session.execute(
                select(func.count()).select_from(AircraftRegistry)
                .where(AircraftRegistry.manufacturer.isnot(None))
            ).scalar()
            return (count or 0) == 0
        except Exception:
            logger.exception("Could not check aircraft_registry row count")
            return False
        finally:
            session.close()

    def seed_stale_sources(self, force_aircraft: bool = False) -> None:
        for spec in self._sources:
            force = force_aircraft and spec.is_aircraft_source
            self._maybe_seed(spec, force=force)

    def _maybe_seed(self, spec: DataSourceSpec, *, force: bool = False) -> None:
        if not force and not self._should_seed(spec):
            return

        logger.info("Seeding data source: %s", spec.source)
        try:
            count = spec.seed_fn()
            logger.info("Seeded %s: %d rows", spec.source, count)
        except Exception:
            logger.exception("Failed to seed data source: %s", spec.source)

    def _should_seed(self, spec: DataSourceSpec) -> bool:
        session = self._session_maker()
        try:
            record = session.get(DataSyncLog, spec.source)
            if record is None or record.last_synced_at is None:
                return True

            last_synced = record.last_synced_at
            if last_synced.tzinfo is None:
                last_synced = last_synced.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - last_synced
            effective_max_age = (
                spec.max_age if record.last_sync_status == "ok" else self._failed_retry
            )
            return age >= effective_max_age
        except Exception:
            logger.exception("Error checking sync log for source %s, seeding anyway", spec.source)
            return True
        finally:
            session.close()
