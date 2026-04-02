from __future__ import annotations

import gzip
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AircraftRegistry, AircraftType
from app.schemas import normalize_icao24
from app.services.aircraft_categories import normalize_aircraft_category_code


class AircraftEnrichmentService:
    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self.settings = settings
        self.session = session or requests.Session()
        self._snapshot_index: dict[str, dict[str, Any]] | None = None
        self._snapshot_loaded_from: Path | None = None

    def close(self) -> None:
        self.session.close()

    def warm_cache(self, allow_download: bool = False) -> None:
        try:
            self._load_snapshot_index(allow_download=allow_download)
        except Exception:
            return

    def enrich(self, db_session: Session, icao24: str) -> AircraftRegistry | None:
        normalized = normalize_icao24(icao24)

        cached = db_session.get(AircraftRegistry, normalized)
        if cached is not None:
            self._fill_from_aircraft_type(db_session, cached)
            return cached

        provider_record = self._lookup_provider_record(normalized)
        if provider_record is None:
            return None

        registry = AircraftRegistry(
            icao24=normalized,
            registration=self._coerce_optional(provider_record.get("registration")),
            type_code=self._normalize_type_code(provider_record.get("type_code")),
            manufacturer=self._coerce_optional(provider_record.get("manufacturer")),
            model=self._coerce_optional(provider_record.get("model")),
            category=normalize_aircraft_category_code(self._coerce_optional(provider_record.get("category"))),
        )
        self._fill_from_aircraft_type(db_session, registry)
        db_session.add(registry)
        db_session.flush()
        return registry

    def _lookup_provider_record(self, icao24: str) -> dict[str, Any] | None:
        try:
            snapshot_index = self._load_snapshot_index()
        except Exception:
            return None

        record = snapshot_index.get(icao24)
        if record is None:
            return None

        return {
            "registration": self._first_present(record, "registration", "reg"),
            "type_code": self._first_present(record, "type_code", "icaoType", "icaotype"),
            "manufacturer": self._first_present(record, "manufacturer", "make"),
            "model": self._first_present(record, "model", "desc", "description"),
            "category": self._derive_category(record),
        }

    def _load_snapshot_index(self, allow_download: bool = True) -> dict[str, dict[str, Any]]:
        snapshot_path = self._ensure_snapshot_path(allow_download=allow_download)
        if self._snapshot_index is not None and self._snapshot_loaded_from == snapshot_path:
            return self._snapshot_index

        with gzip.open(snapshot_path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)

        snapshot_index = self._build_index(payload)
        self._snapshot_index = snapshot_index
        self._snapshot_loaded_from = snapshot_path
        return snapshot_index

    def _ensure_snapshot_path(self, allow_download: bool = True) -> Path:
        snapshot_path = self.settings.adsbx_snapshot_path
        self.settings.ensure_directories()

        if snapshot_path.exists():
            max_age = timedelta(hours=self.settings.adsbx_snapshot_max_age_hours)
            modified_at = datetime.fromtimestamp(snapshot_path.stat().st_mtime, tz=timezone.utc)
            if datetime.now(timezone.utc) - modified_at <= max_age:
                return snapshot_path

        if not allow_download:
            raise FileNotFoundError(snapshot_path)

        temp_path = snapshot_path.with_suffix(".tmp")
        try:
            with self.session.get(self.settings.adsbx_db_url, stream=True, timeout=30) as response:
                response.raise_for_status()
                with temp_path.open("wb") as handle:
                    shutil.copyfileobj(response.raw, handle)
        except Exception:
            if snapshot_path.exists():
                return snapshot_path
            raise

        temp_path.replace(snapshot_path)
        self._snapshot_index = None
        self._snapshot_loaded_from = None
        return snapshot_path

    def _build_index(self, payload: Any) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}

        if isinstance(payload, dict):
            if any(key in payload for key in ("aircraft", "ac", "items", "data")):
                records = payload.get("aircraft") or payload.get("ac") or payload.get("items") or payload.get("data")
                self._consume_records(index, records)
            else:
                for key, value in payload.items():
                    if isinstance(value, dict):
                        normalized = self._safe_normalize_hex(key)
                        if normalized:
                            index[normalized] = value
        elif isinstance(payload, list):
            self._consume_records(index, payload)

        return index

    def _consume_records(self, index: dict[str, dict[str, Any]], records: Any) -> None:
        if isinstance(records, dict):
            for key, value in records.items():
                if isinstance(value, dict):
                    normalized = self._safe_normalize_hex(key)
                    if normalized:
                        index[normalized] = value
            return

        if not isinstance(records, list):
            return

        for item in records:
            if not isinstance(item, dict):
                continue
            raw_hex = self._first_present(item, "icao24", "icao", "hex")
            normalized = self._safe_normalize_hex(raw_hex)
            if normalized:
                index[normalized] = item

    def _fill_from_aircraft_type(self, db_session: Session, registry: AircraftRegistry) -> None:
        if not registry.type_code:
            return

        aircraft_type = db_session.get(AircraftType, registry.type_code)
        if aircraft_type is None:
            return

        if not registry.manufacturer:
            registry.manufacturer = aircraft_type.manufacturer
        if not registry.model:
            registry.model = aircraft_type.model
        if not registry.category:
            registry.category = normalize_aircraft_category_code(aircraft_type.category)

    @staticmethod
    def _first_present(record: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = record.get(key)
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def _coerce_optional(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _normalize_type_code(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip().upper()
        return text or None

    @staticmethod
    def _derive_category(record: dict[str, Any]) -> str | None:
        for key in ("short_type", "category", "wtc", "species"):
            value = record.get(key)
            if value not in (None, ""):
                return str(value).strip()
        return None

    @staticmethod
    def _safe_normalize_hex(value: Any) -> str | None:
        if value is None:
            return None
        try:
            return normalize_icao24(str(value))
        except ValueError:
            return None
