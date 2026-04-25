from __future__ import annotations

import csv
import io
import logging
import socket
import time
import zipfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import requests
from sqlalchemy.exc import DataError as SQLAlchemyDataError
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
SOURCE_OPENFLIGHTS_ROUTES = "openflights_routes"
MAX_SYNC_ERROR_LENGTH = 4000
AIRCRAFT_REGISTRY_MAX_LENGTHS: dict[str, int] = {
    "icao24": 6,
    "registration": 32,
    "type_code": 8,
    "manufacturer": 128,
    "model": 128,
    "category": 16,
    "operator": 128,
    "operator_icao": 8,
    "operator_iata": 8,
    "operator_callsign": 64,
    "owner": 128,
    "serial_number": 32,
    "year_built": 4,
    "engines": 128,
    "icao_aircraft_type": 8,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iter_exception_chain(exc: BaseException) -> Iterator[BaseException]:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


class DataSeeder:
    def __init__(self, settings: Settings, session_maker: sessionmaker[Session]) -> None:
        self._settings = settings
        self._session_maker = session_maker
        self._http = requests.Session()
        self._http.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    def close(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------
    # Public seed methods
    # ------------------------------------------------------------------

    def seed_opensky_aircraft(self) -> int:
        """Stream OpenSky aircraft metadata CSV and upsert into aircraft_registry."""
        url = self._settings.opensky_aircraft_db_url
        if not url:
            logger.info("OpenSky aircraft URL not configured, skipping")
            self._mark_sync(SOURCE_OPENSKY_AIRCRAFT, "unavailable", None, "URL not configured")
            return 0
        logger.info("Starting OpenSky aircraft seed from %s", url)
        max_attempts = max(1, self._settings.opensky_seed_retry_attempts)
        base_delay = max(0.0, self._settings.opensky_seed_retry_base_delay_seconds)

        for attempt in range(1, max_attempts + 1):
            total = 0
            batch: list[dict] = []
            try:
                for row in self._stream_csv_rows(url):
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
                    category = self._normalize_seed_category(raw_category)
                    operator = row.get("operator", "").strip() or None
                    operator_icao = row.get("operatoricao", "").strip().upper() or None
                    operator_iata = row.get("operatoriata", "").strip().upper() or None
                    operator_callsign = row.get("operatorcallsign", "").strip() or None
                    owner = row.get("owner", "").strip() or None
                    serial_number = row.get("serialnumber", "").strip() or None
                    year_built = row.get("built", "").strip()[:4] or None
                    engines = row.get("engines", "").strip() or None
                    icao_aircraft_type = row.get("icaoaircrafttype", "").strip().upper() or None

                    now = _utcnow()
                    batch.append({
                        "icao24": self._truncate_string("icao24", icao24),
                        "registration": self._truncate_string("registration", registration),
                        "type_code": self._truncate_string("type_code", type_code),
                        "manufacturer": self._truncate_string("manufacturer", manufacturer),
                        "model": self._truncate_string("model", model),
                        "category": self._truncate_string("category", category),
                        "operator": self._truncate_string("operator", operator),
                        "operator_icao": self._truncate_string("operator_icao", operator_icao),
                        "operator_iata": self._truncate_string("operator_iata", operator_iata),
                        "operator_callsign": self._truncate_string("operator_callsign", operator_callsign),
                        "owner": self._truncate_string("owner", owner),
                        "serial_number": self._truncate_string("serial_number", serial_number),
                        "year_built": self._truncate_string("year_built", year_built),
                        "engines": self._truncate_string("engines", engines),
                        "icao_aircraft_type": self._truncate_string("icao_aircraft_type", icao_aircraft_type),
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
                category = self._classify_exception(exc)
                message = self._format_sync_error(category, url, exc)
                if self._is_retryable_network_error(exc) and attempt < max_attempts:
                    logger.warning(
                        "seed_opensky_aircraft transient failure (%s) on attempt %d/%d for %s: %s",
                        category,
                        attempt,
                        max_attempts,
                        url,
                        exc,
                    )
                    if base_delay > 0:
                        time.sleep(base_delay * (2 ** (attempt - 1)))
                    continue

                status = self._status_for_exception(exc)
                logger.exception(
                    "seed_opensky_aircraft failed (%s) for %s after %d attempt(s)",
                    category,
                    url,
                    attempt,
                )
                self._mark_sync(SOURCE_OPENSKY_AIRCRAFT, status, total or None, message)
                if status == "unavailable":
                    return 0
                raise

    def seed_faa_aircraft(self) -> int:
        """Download FAA ReleasableAircraft ZIP, extract MASTER.txt, upsert into aircraft_registry.

        Only populates icao24 + registration; FAA data doesn't include manufacturer/model
        without the ACFTREF cross-reference table. The upsert preserves existing richer data.
        """
        if not self._settings.faa_aircraft_zip_url:
            logger.info("FAA aircraft URL not configured, skipping")
            self._mark_sync(SOURCE_FAA_AIRCRAFT, "unavailable", None, "URL not configured")
            return 0

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
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code < 500:
                msg = str(exc)
                logger.warning("seed_faa_aircraft: source unavailable (%s)", msg)
                self._mark_sync(SOURCE_FAA_AIRCRAFT, "unavailable", None, msg)
                return 0
            msg = str(exc)
            logger.exception("seed_faa_aircraft failed")
            self._mark_sync(SOURCE_FAA_AIRCRAFT, "error", None, msg)
            raise
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
        if not self._settings.ourairports_url:
            logger.info("OurAirports URL not configured, skipping")
            self._mark_sync(SOURCE_OURAIRPORTS, "unavailable", None, "URL not configured")
            return 0

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
        """Stream a route database CSV (callsign, adep, ades) and upsert into flight_routes.

        The OpenSky route database is no longer publicly available. Set OPENSKY_ROUTES_URL
        to point to an alternative CSV source with callsign/adep/ades columns.
        """
        if not self._settings.opensky_routes_url:
            logger.info("Route database URL not configured (OPENSKY_ROUTES_URL), skipping")
            self._mark_sync(SOURCE_OPENSKY_ROUTES, "unavailable", None, "URL not configured")
            return 0

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
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code < 500:
                msg = str(exc)
                logger.warning(
                    "seed_routes: source unavailable (%s). "
                    "Set OPENSKY_ROUTES_URL to a CSV with callsign/adep/ades columns.",
                    msg,
                )
                self._mark_sync(SOURCE_OPENSKY_ROUTES, "unavailable", None, msg)
                return 0
            msg = str(exc)
            logger.exception("seed_routes failed")
            self._mark_sync(SOURCE_OPENSKY_ROUTES, "error", None, msg)
            raise
        except Exception as exc:
            msg = str(exc)
            logger.exception("seed_routes failed")
            self._mark_sync(SOURCE_OPENSKY_ROUTES, "error", total or None, msg)
            raise

    def seed_openflights_routes(self) -> int:
        """Seed airline route data from OpenFlights routes.dat into flight_routes.

        routes.dat maps airline/src-airport/dst-airport using mostly IATA codes.
        We convert to ICAO using airlines.dat (IATA→ICAO airline) and the airports
        table (IATA→ICAO airport).  The primary key stored is
        ``{airline_icao}/{dep_icao}/{arr_icao}`` (e.g. ``BAW/EGLL/KJFK``).

        Auto-fill in create_log then looks up by prefix ``{airline_icao}/%`` when no
        exact callsign match exists.
        """
        if not self._settings.openflights_routes_url:
            logger.info("OpenFlights routes URL not configured, skipping")
            self._mark_sync(SOURCE_OPENFLIGHTS_ROUTES, "unavailable", None, "URL not configured")
            return 0

        logger.info("Starting OpenFlights route seed")
        total = 0
        batch: list[dict] = []
        try:
            # Build IATA airline code → ICAO airline code mapping from airlines.dat
            airline_iata_to_icao: dict[str, str] = {}
            if self._settings.openflights_airlines_url:
                # airlines.dat columns (no header): airline_id,name,alias,iata,icao,callsign,country,active
                for row in self._stream_csv_rows_noheader(
                    self._settings.openflights_airlines_url,
                    ["airline_id", "name", "alias", "iata", "icao", "callsign", "country", "active"],
                ):
                    iata = row.get("iata", "").strip().upper()
                    icao = row.get("icao", "").strip().upper()
                    if iata and icao and iata != "\\N" and icao != "\\N":
                        airline_iata_to_icao[iata] = icao

            # Build IATA airport code → ICAO ident mapping from the airports table
            airport_iata_to_icao: dict[str, str] = {}
            session = self._session_maker()
            try:
                from app.models import Airport
                from sqlalchemy import select
                rows = session.execute(
                    select(Airport.iata_code, Airport.ident).where(Airport.iata_code.isnot(None))
                ).all()
                for iata_code, ident in rows:
                    if iata_code:
                        airport_iata_to_icao[iata_code.upper()] = ident.upper()
            finally:
                session.close()

            # routes.dat columns (no header): airline,airline_id,src_airport,src_airport_id,
            #                                  dst_airport,dst_airport_id,codeshare,stops,equipment
            for row in self._stream_csv_rows_noheader(
                self._settings.openflights_routes_url,
                ["airline", "airline_id", "src_airport", "src_airport_id",
                 "dst_airport", "dst_airport_id", "codeshare", "stops", "equipment"],
            ):
                airline_raw = row.get("airline", "").strip().upper()
                src_raw = row.get("src_airport", "").strip().upper()
                dst_raw = row.get("dst_airport", "").strip().upper()

                if not airline_raw or not src_raw or not dst_raw:
                    continue
                if airline_raw == "\\N" or src_raw == "\\N" or dst_raw == "\\N":
                    continue

                # Resolve airline to ICAO (3-letter); already ICAO if len==3, else look up
                if len(airline_raw) == 3:
                    airline_icao = airline_raw
                else:
                    airline_icao = airline_iata_to_icao.get(airline_raw)
                    if not airline_icao:
                        continue

                # Resolve airports to ICAO (4-letter); already ICAO if len==4, else look up
                dep_icao = src_raw if len(src_raw) == 4 else airport_iata_to_icao.get(src_raw)
                arr_icao = dst_raw if len(dst_raw) == 4 else airport_iata_to_icao.get(dst_raw)
                if not dep_icao or not arr_icao:
                    continue

                callsign_key = f"{airline_icao}/{dep_icao}/{arr_icao}"
                if len(callsign_key) > 16:
                    continue

                now = _utcnow()
                batch.append({
                    "callsign": callsign_key,
                    "departure_icao": dep_icao,
                    "arrival_icao": arr_icao,
                    "last_updated": now,
                })
                total += 1

                if len(batch) >= self._settings.data_seed_batch_size:
                    self._upsert_batch(FlightRoute, batch)
                    batch = []
                    if total % 50_000 == 0:
                        logger.info("seed_openflights_routes: processed %d rows", total)

            if batch:
                self._upsert_batch(FlightRoute, batch)

            logger.info("seed_openflights_routes complete: %d rows", total)
            self._mark_sync(SOURCE_OPENFLIGHTS_ROUTES, "ok", total, None)
            return total
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code < 500:
                msg = str(exc)
                logger.warning("seed_openflights_routes: source unavailable (%s)", msg)
                self._mark_sync(SOURCE_OPENFLIGHTS_ROUTES, "unavailable", None, msg)
                return 0
            msg = str(exc)
            logger.exception("seed_openflights_routes failed")
            self._mark_sync(SOURCE_OPENFLIGHTS_ROUTES, "error", None, msg)
            raise
        except Exception as exc:
            msg = str(exc)
            logger.exception("seed_openflights_routes failed")
            self._mark_sync(SOURCE_OPENFLIGHTS_ROUTES, "error", total or None, msg)
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

    def _stream_csv_rows_noheader(self, url: str, fieldnames: list[str], timeout: int = 60) -> Iterator[dict[str, str]]:
        """Stream a headerless CSV, mapping columns by position to fieldnames."""
        with self._http.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines():
                line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else raw_line
                if not line.strip():
                    continue
                parsed = next(csv.reader([line]))
                if len(parsed) >= len(fieldnames):
                    yield dict(zip(fieldnames, parsed))

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

    def _is_retryable_network_error(self, exc: BaseException) -> bool:
        if isinstance(exc, requests.Timeout):
            return True
        if isinstance(exc, requests.ConnectionError) and not isinstance(exc, requests.HTTPError):
            return True
        return any(isinstance(error, socket.gaierror) for error in _iter_exception_chain(exc))

    def _classify_exception(self, exc: BaseException) -> str:
        if any(isinstance(error, socket.gaierror) for error in _iter_exception_chain(exc)):
            return "dns_error"
        if isinstance(exc, requests.Timeout):
            return "timeout_error"
        if isinstance(exc, requests.HTTPError):
            return "http_error"
        if isinstance(exc, requests.ConnectionError):
            return "connection_error"
        return "parse_error"

    def _status_for_exception(self, exc: BaseException) -> str:
        if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code < 500:
            return "unavailable"
        return "error"

    def _format_sync_error(self, category: str, url: str, exc: BaseException) -> str:
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            return f"{category}: HTTP {exc.response.status_code} while fetching {url}"
        if isinstance(exc, SQLAlchemyDataError):
            detail = str(getattr(exc, "orig", exc))
        else:
            detail = str(exc)
        message = f"{category}: {detail} (url={url})"
        if len(message) > MAX_SYNC_ERROR_LENGTH:
            message = f"{message[:MAX_SYNC_ERROR_LENGTH - 3]}..."
        return message

    def _normalize_seed_category(self, raw_category: str | None) -> str | None:
        normalized = normalize_aircraft_category_code(raw_category)
        if normalized is None:
            return None
        return normalized if len(normalized) <= 16 else None

    def _truncate_string(self, field: str, value: str | None) -> str | None:
        if value is None:
            return None
        max_length = AIRCRAFT_REGISTRY_MAX_LENGTHS.get(field)
        if max_length is None or len(value) <= max_length:
            return value
        return value[:max_length]

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
                    operator=stmt.inserted.operator,
                    operator_icao=stmt.inserted.operator_icao,
                    operator_iata=stmt.inserted.operator_iata,
                    operator_callsign=stmt.inserted.operator_callsign,
                    owner=stmt.inserted.owner,
                    serial_number=stmt.inserted.serial_number,
                    year_built=stmt.inserted.year_built,
                    engines=stmt.inserted.engines,
                    icao_aircraft_type=stmt.inserted.icao_aircraft_type,
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
                        existing.operator = row.get("operator") or existing.operator
                        existing.operator_icao = row.get("operator_icao") or existing.operator_icao
                        existing.operator_iata = row.get("operator_iata") or existing.operator_iata
                        existing.operator_callsign = row.get("operator_callsign") or existing.operator_callsign
                        existing.owner = row.get("owner") or existing.owner
                        existing.serial_number = row.get("serial_number") or existing.serial_number
                        existing.year_built = row.get("year_built") or existing.year_built
                        existing.engines = row.get("engines") or existing.engines
                        existing.icao_aircraft_type = row.get("icao_aircraft_type") or existing.icao_aircraft_type
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
