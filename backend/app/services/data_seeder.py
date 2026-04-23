from __future__ import annotations

import csv
import io
import logging
import zipfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import requests
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models import Airport, AircraftRegistry, DataSyncLog, FlightRoute
from app.schemas import normalize_icao24
from app.services.aircraft_categories import normalize_aircraft_category_code

logger = logging.getLogger(__name__)

SOURCE_OPENSKY_AIRCRAFT = "opensky_aircraft"
SOURCE_FAA_AIRCRAFT = "faa_aircraft"
SOURCE_OURAIRPORTS = "ourairports"
SOURCE_OPENSKY_ROUTES = "opensky_routes"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DataSeeder:
    def __init__(self, settings: Settings, session_maker: sessionmaker[Session]) -> None:
        self._settings = settings
        self._session_maker = session_maker
        self._http = requests.Session()

    def close(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------
    # Public seed methods
    # ------------------------------------------------------------------

    def seed_opensky_aircraft(self) -> int:
        """Stream OpenSky aircraft metadata CSV and upsert into aircraft_registry."""
        logger.info("Starting OpenSky aircraft seed from %s", self._settings.opensky_aircraft_db_url)
        total = 0
        batch: list[dict] = []
        try:
            for row in self._stream_csv_rows(self._settings.opensky_aircraft_db_url):
                raw_icao24 = row.get("icao24", "").strip()
                try:
                    icao24 = normalize_icao24(raw_icao24)
                except ValueError:
                    continue

                registration = row.get("registration", "").strip() or None
                manufacturer = row.get("manufacturername", "").strip() or None
                model = row.get("model", "").strip() or None
                raw_type = row.get("typecode", "").strip()
                type_code = raw_type.upper() or None
                raw_category = row.get("categoryDescription", "").strip() or None
                category = normalize_aircraft_category_code(raw_category)

                now = _utcnow()
                batch.append({
                    "icao24": icao24,
                    "registration": registration,
                    "type_code": type_code,
                    "manufacturer": manufacturer,
                    "model": model,
                    "category": category,
                    "first_seen": now,
                    "last_updated": now,
                })
                total += 1

                if len(batch) >= self._settings.data_seed_batch_size:
                    self._upsert_aircraft_batch(batch)
                    batch = []
                    if total % 50_000 == 0:
                        logger.info("seed_opensky_aircraft: processed %d rows", total)

            if batch:
                self._upsert_aircraft_batch(batch)

            logger.info("seed_opensky_aircraft complete: %d rows", total)
            self._mark_sync(SOURCE_OPENSKY_AIRCRAFT, "ok", total, None)
            return total
        except Exception as exc:
            msg = str(exc)
            logger.exception("seed_opensky_aircraft failed")
            self._mark_sync(SOURCE_OPENSKY_AIRCRAFT, "error", total or None, msg)
            raise

    def seed_faa_aircraft(self) -> int:
        """Download FAA ReleasableAircraft ZIP, extract MASTER.txt, upsert into aircraft_registry.

        Only populates icao24 + registration; FAA data doesn't include manufacturer/model
        without the ACFTREF cross-reference table. The upsert preserves existing richer data.
        """
        logger.info("Starting FAA aircraft seed from %s", self._settings.faa_aircraft_zip_url)
        zip_path = self._settings.faa_aircraft_zip_path
        self._settings.ensure_directories()
        total = 0
        try:
            self._download_file(self._settings.faa_aircraft_zip_url, zip_path)
            total = self._import_faa_zip(zip_path)
            logger.info("seed_faa_aircraft complete: %d rows", total)
            self._mark_sync(SOURCE_FAA_AIRCRAFT, "ok", total, None)
            return total
        except Exception as exc:
            msg = str(exc)
            logger.exception("seed_faa_aircraft failed")
            self._mark_sync(SOURCE_FAA_AIRCRAFT, "error", total or None, msg)
            raise
        finally:
            if zip_path.exists():
                try:
                    zip_path.unlink()
                except OSError:
                    pass

    def seed_airports(self) -> int:
        """Stream OurAirports airports.csv and upsert into airports table."""
        logger.info("Starting airports seed from %s", self._settings.ourairports_url)
        total = 0
        batch: list[dict] = []
        try:
            for row in self._stream_csv_rows(self._settings.ourairports_url):
                ident = row.get("ident", "").strip()
                if not ident:
                    continue

                try:
                    lat = float(row["latitude_deg"]) if row.get("latitude_deg", "").strip() else None
                    lon = float(row["longitude_deg"]) if row.get("longitude_deg", "").strip() else None
                    elev_raw = row.get("elevation_ft", "").strip()
                    elev = int(float(elev_raw)) if elev_raw else None
                except (ValueError, KeyError):
                    lat = lon = elev = None

                now = _utcnow()
                batch.append({
                    "ident": ident,
                    "type": row.get("type", "").strip() or None,
                    "name": row.get("name", "").strip() or None,
                    "latitude_deg": lat,
                    "longitude_deg": lon,
                    "elevation_ft": elev,
                    "continent": row.get("continent", "").strip() or None,
                    "iso_country": row.get("iso_country", "").strip() or None,
                    "municipality": row.get("municipality", "").strip() or None,
                    "iata_code": row.get("iata_code", "").strip() or None,
                    "last_updated": now,
                })
                total += 1

                if len(batch) >= self._settings.data_seed_batch_size:
                    self._upsert_batch(Airport, batch)
                    batch = []

            if batch:
                self._upsert_batch(Airport, batch)

            logger.info("seed_airports complete: %d rows", total)
            self._mark_sync(SOURCE_OURAIRPORTS, "ok", total, None)
            return total
        except Exception as exc:
            msg = str(exc)
            logger.exception("seed_airports failed")
            self._mark_sync(SOURCE_OURAIRPORTS, "error", total or None, msg)
            raise

    def seed_routes(self) -> int:
        """Stream OpenSky route database CSV and upsert into flight_routes table."""
        logger.info("Starting route seed from %s", self._settings.opensky_routes_url)
        total = 0
        batch: list[dict] = []
        try:
            for row in self._stream_csv_rows(self._settings.opensky_routes_url):
                callsign = row.get("callsign", "").strip().upper()
                if not callsign:
                    continue

                departure = row.get("adep", "").strip().upper() or None
                arrival = row.get("ades", "").strip().upper() or None
                now = _utcnow()
                batch.append({
                    "callsign": callsign,
                    "departure_icao": departure,
                    "arrival_icao": arrival,
                    "last_updated": now,
                })
                total += 1

                if len(batch) >= self._settings.data_seed_batch_size:
                    self._upsert_batch(FlightRoute, batch)
                    batch = []
                    if total % 50_000 == 0:
                        logger.info("seed_routes: processed %d rows", total)

            if batch:
                self._upsert_batch(FlightRoute, batch)

            logger.info("seed_routes complete: %d rows", total)
            self._mark_sync(SOURCE_OPENSKY_ROUTES, "ok", total, None)
            return total
        except Exception as exc:
            msg = str(exc)
            logger.exception("seed_routes failed")
            self._mark_sync(SOURCE_OPENSKY_ROUTES, "error", total or None, msg)
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _stream_csv_rows(self, url: str, timeout: int = 60) -> Iterator[dict[str, str]]:
        with self._http.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            header: list[str] | None = None
            for raw_line in response.iter_lines():
                line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else raw_line
                if not line.strip():
                    continue
                parsed = next(csv.reader([line]))
                if header is None:
                    header = parsed
                    continue
                if len(parsed) == len(header):
                    yield dict(zip(header, parsed))

    def _download_file(self, url: str, dest: Path, timeout: int = 120) -> None:
        import shutil
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        try:
            with self._http.get(url, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                with tmp.open("wb") as fh:
                    shutil.copyfileobj(response.raw, fh)
            tmp.replace(dest)
        except Exception:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise

    def _import_faa_zip(self, zip_path: Path) -> int:
        total = 0
        batch: list[dict] = []
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            master_name = next((n for n in names if n.upper() == "MASTER.txt".upper()), None)
            if master_name is None:
                raise FileNotFoundError("MASTER.txt not found in FAA ZIP")
            with zf.open(master_name) as raw:
                text_file = io.TextIOWrapper(raw, encoding="latin-1")
                reader = csv.DictReader(text_file)
                for row in reader:
                    raw_hex = (row.get("MODE S CODE HEX") or row.get("MODE S CODE") or "").strip()
                    if not raw_hex:
                        continue
                    try:
                        icao24 = normalize_icao24(raw_hex)
                    except ValueError:
                        continue

                    n_number = (row.get("N-NUMBER") or "").strip()
                    registration = f"N{n_number}" if n_number else None
                    now = _utcnow()
                    batch.append({
                        "icao24": icao24,
                        "registration": registration,
                        "first_seen": now,
                        "last_updated": now,
                    })
                    total += 1

                    if len(batch) >= self._settings.data_seed_batch_size:
                        self._upsert_aircraft_batch_faa(batch)
                        batch = []
                        if total % 50_000 == 0:
                            logger.info("seed_faa_aircraft: processed %d rows", total)

        if batch:
            self._upsert_aircraft_batch_faa(batch)
        return total

    def _upsert_aircraft_batch(self, rows: list[dict]) -> None:
        """Upsert into aircraft_registry, updating all fields except first_seen on conflict."""
        session = self._session_maker()
        try:
            dialect = session.bind.dialect.name  # type: ignore[union-attr]
            if dialect == "mysql":
                from sqlalchemy.dialects.mysql import insert as mysql_insert
                stmt = mysql_insert(AircraftRegistry.__table__).values(rows)
                stmt = stmt.on_duplicate_key_update(
                    registration=stmt.inserted.registration,
                    type_code=stmt.inserted.type_code,
                    manufacturer=stmt.inserted.manufacturer,
                    model=stmt.inserted.model,
                    category=stmt.inserted.category,
                    last_updated=stmt.inserted.last_updated,
                )
                session.execute(stmt)
            else:
                for row in rows:
                    existing = session.get(AircraftRegistry, row["icao24"])
                    if existing is None:
                        session.add(AircraftRegistry(**row))
                    else:
                        existing.registration = row.get("registration") or existing.registration
                        existing.type_code = row.get("type_code") or existing.type_code
                        existing.manufacturer = row.get("manufacturer") or existing.manufacturer
                        existing.model = row.get("model") or existing.model
                        existing.category = row.get("category") or existing.category
                        existing.last_updated = row["last_updated"]
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _upsert_aircraft_batch_faa(self, rows: list[dict]) -> None:
        """FAA upsert: only set registration where it is currently NULL or missing."""
        session = self._session_maker()
        try:
            dialect = session.bind.dialect.name  # type: ignore[union-attr]
            if dialect == "mysql":
                from sqlalchemy.dialects.mysql import insert as mysql_insert
                from sqlalchemy import func
                stmt = mysql_insert(AircraftRegistry.__table__).values(rows)
                stmt = stmt.on_duplicate_key_update(
                    registration=func.coalesce(
                        AircraftRegistry.__table__.c.registration,
                        stmt.inserted.registration,
                    ),
                    last_updated=stmt.inserted.last_updated,
                )
                session.execute(stmt)
            else:
                for row in rows:
                    existing = session.get(AircraftRegistry, row["icao24"])
                    if existing is None:
                        session.add(AircraftRegistry(**row))
                    elif not existing.registration and row.get("registration"):
                        existing.registration = row["registration"]
                        existing.last_updated = row["last_updated"]
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _upsert_batch(self, model_class: type, rows: list[dict]) -> None:
        """Generic full-replace upsert for Airport and FlightRoute."""
        session = self._session_maker()
        try:
            dialect = session.bind.dialect.name  # type: ignore[union-attr]
            if dialect == "mysql":
                from sqlalchemy.dialects.mysql import insert as mysql_insert
                stmt = mysql_insert(model_class.__table__).values(rows)
                pk_cols = {col.name for col in model_class.__table__.primary_key}
                update_dict = {
                    col.name: stmt.inserted[col.name]
                    for col in model_class.__table__.columns
                    if col.name not in pk_cols
                }
                stmt = stmt.on_duplicate_key_update(**update_dict)
                session.execute(stmt)
            else:
                for row in rows:
                    session.merge(model_class(**row))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _mark_sync(
        self,
        source: str,
        status: str,
        row_count: int | None,
        error: str | None,
    ) -> None:
        session = self._session_maker()
        try:
            record = session.get(DataSyncLog, source)
            if record is None:
                record = DataSyncLog(source=source)
                session.add(record)
            record.last_synced_at = _utcnow()
            record.last_sync_status = status
            record.last_sync_error = error
            record.row_count = row_count
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Failed to write sync log for source: %s", source)
        finally:
            session.close()
