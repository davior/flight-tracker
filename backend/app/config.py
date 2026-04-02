from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


DEFAULT_DATABASE_URL = "mysql+mysqlconnector://flightuser:flightpass@db:3306/flightlogs"
DEFAULT_ADSBX_DB_URL = "https://downloads.adsbexchange.com/downloads/basic-ac-db.json.gz"


def _default_upload_dir() -> Path:
    if Path("/app").exists():
        return Path("/app/uploads")
    return Path(__file__).resolve().parents[2] / "uploads"


def _default_runtime_dir() -> Path:
    return Path(os.getenv("RUNTIME_DIR", "/tmp/flight-logger-cache"))


@dataclass(slots=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    upload_dir: Path = _default_upload_dir()
    runtime_dir: Path = _default_runtime_dir()
    db_startup_max_attempts: int = 30
    db_startup_retry_delay_seconds: float = 1.0
    max_nearby_radius_km: int = 500
    opensky_client_id: str | None = None
    opensky_client_secret: str | None = None
    adsbx_db_url: str = DEFAULT_ADSBX_DB_URL
    adsbx_snapshot_max_age_hours: int = 24

    @property
    def adsbx_snapshot_path(self) -> Path:
        return self.runtime_dir / "basic-ac-db.json.gz"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
            upload_dir=Path(os.getenv("UPLOAD_DIR", _default_upload_dir())),
            runtime_dir=Path(os.getenv("RUNTIME_DIR", _default_runtime_dir())),
            db_startup_max_attempts=int(os.getenv("DB_STARTUP_MAX_ATTEMPTS", "30")),
            db_startup_retry_delay_seconds=float(os.getenv("DB_STARTUP_RETRY_DELAY_SECONDS", "1.0")),
            max_nearby_radius_km=int(os.getenv("MAX_NEARBY_RADIUS_KM", "500")),
            opensky_client_id=os.getenv("OPENSKY_CLIENT_ID"),
            opensky_client_secret=os.getenv("OPENSKY_CLIENT_SECRET"),
            adsbx_db_url=os.getenv("ADSBX_DB_URL", DEFAULT_ADSBX_DB_URL),
            adsbx_snapshot_max_age_hours=int(os.getenv("ADSBX_SNAPSHOT_MAX_AGE_HOURS", "24")),
        )

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings.from_env()
    settings.ensure_directories()
    return settings
