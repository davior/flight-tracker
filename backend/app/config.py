from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus


DEFAULT_DATABASE_URL = "mysql+pymysql://flightuser:flightpass@db:3306/flightlogs"


def _build_database_url() -> str:
    # If DATABASE_URL is set directly (e.g. dev docker-compose), use it as-is.
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Otherwise build from individual vars, URL-encoding the password so special
    # characters like '@' and '$' don't corrupt the connection string.
    password = quote_plus(os.getenv("MYSQL_PASSWORD", "flightpass"))
    user = os.getenv("DB_USER", "flightuser")
    host = os.getenv("DB_HOST", "db")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "flightlogs")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"


DEFAULT_ADSBX_DB_URL = "https://downloads.adsbexchange.com/downloads/basic-ac-db.json.gz"
DEFAULT_ADSBX_API_BASE_URL = "https://adsbexchange.com/api/aircraft"

DEFAULT_OPENSKY_AIRCRAFT_DB_URL = "https://s3.opensky-network.org/data-samples/metadata/aircraftDatabase.csv"
DEFAULT_FAA_AIRCRAFT_ZIP_URL = "https://registry.faa.gov/database/ReleasableAircraft.zip"
DEFAULT_OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
# The OpenSky route database (callsign→adep/ades) is no longer publicly available.
# Set OPENSKY_ROUTES_URL to point to a CSV with callsign/adep/ades columns if you have one.
DEFAULT_OPENSKY_ROUTES_URL = ""

DEFAULT_OPENFLIGHTS_ROUTES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"
DEFAULT_OPENFLIGHTS_AIRLINES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"


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
    live_flight_provider: str = "opensky"
    opensky_client_id: str | None = None
    opensky_client_secret: str | None = None
    adsbx_api_key: str | None = None
    adsbx_api_base_url: str = DEFAULT_ADSBX_API_BASE_URL
    adsbx_db_url: str = DEFAULT_ADSBX_DB_URL
    adsbx_snapshot_max_age_hours: int = 24
    # Data seeding
    opensky_aircraft_db_url: str = DEFAULT_OPENSKY_AIRCRAFT_DB_URL
    faa_aircraft_zip_url: str = DEFAULT_FAA_AIRCRAFT_ZIP_URL
    ourairports_url: str = DEFAULT_OURAIRPORTS_URL
    opensky_routes_url: str = DEFAULT_OPENSKY_ROUTES_URL
    openflights_routes_url: str = DEFAULT_OPENFLIGHTS_ROUTES_URL
    openflights_airlines_url: str = DEFAULT_OPENFLIGHTS_AIRLINES_URL
    aircraft_refresh_interval_hours: int = 168   # 7 days
    airport_refresh_interval_hours: int = 720    # 30 days
    failed_source_retry_hours: int = 1
    opensky_seed_retry_attempts: int = 3
    opensky_seed_retry_base_delay_seconds: float = 1.0
    data_seed_batch_size: int = 1000
    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_days: int = 30
    # Email (SMTP)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "noreply@example.com"
    app_base_url: str = "http://localhost:5173"
    # Google OAuth
    google_client_id: str | None = None
    # Provider config
    providers_config_path: str | None = None
    # Logging
    log_level: str = "INFO"
    log_file: Path | None = None
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5
    # Admin seeding
    admin_email: str = "admin@chemtrail-tracker.com"
    admin_password: str = "change-me-admin-password"
    # AI provider (deepseek | ollama | openai)
    ai_provider: str = "deepseek"
    ai_model: str = "deepseek-chat"
    ai_api_key: str | None = None
    ai_base_url: str | None = None
    # Threat detection
    auto_block_requests_per_minute: int = 300
    auto_block_release_hours: int = 24

    @property
    def adsbx_snapshot_path(self) -> Path:
        return self.runtime_dir / "basic-ac-db.json.gz"

    @property
    def faa_aircraft_zip_path(self) -> Path:
        return self.runtime_dir / "faa_releasable.zip"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=_build_database_url(),
            upload_dir=Path(os.getenv("UPLOAD_DIR", _default_upload_dir())),
            runtime_dir=Path(os.getenv("RUNTIME_DIR", _default_runtime_dir())),
            db_startup_max_attempts=int(os.getenv("DB_STARTUP_MAX_ATTEMPTS", "30")),
            db_startup_retry_delay_seconds=float(os.getenv("DB_STARTUP_RETRY_DELAY_SECONDS", "1.0")),
            max_nearby_radius_km=int(os.getenv("MAX_NEARBY_RADIUS_KM", "500")),
            live_flight_provider=os.getenv("LIVE_FLIGHT_PROVIDER", "opensky"),
            opensky_client_id=os.getenv("OPENSKY_CLIENT_ID"),
            opensky_client_secret=os.getenv("OPENSKY_CLIENT_SECRET"),
            adsbx_api_key=os.getenv("ADSBX_API_KEY"),
            adsbx_api_base_url=os.getenv("ADSBX_API_BASE_URL", DEFAULT_ADSBX_API_BASE_URL),
            adsbx_db_url=os.getenv("ADSBX_DB_URL", DEFAULT_ADSBX_DB_URL),
            adsbx_snapshot_max_age_hours=int(os.getenv("ADSBX_SNAPSHOT_MAX_AGE_HOURS", "24")),
            opensky_aircraft_db_url=os.getenv("OPENSKY_AIRCRAFT_DB_URL", DEFAULT_OPENSKY_AIRCRAFT_DB_URL),
            faa_aircraft_zip_url=os.getenv("FAA_AIRCRAFT_ZIP_URL", DEFAULT_FAA_AIRCRAFT_ZIP_URL),
            ourairports_url=os.getenv("OURAIRPORTS_URL", DEFAULT_OURAIRPORTS_URL),
            opensky_routes_url=os.getenv("OPENSKY_ROUTES_URL", DEFAULT_OPENSKY_ROUTES_URL),
            openflights_routes_url=os.getenv("OPENFLIGHTS_ROUTES_URL", DEFAULT_OPENFLIGHTS_ROUTES_URL),
            openflights_airlines_url=os.getenv("OPENFLIGHTS_AIRLINES_URL", DEFAULT_OPENFLIGHTS_AIRLINES_URL),
            aircraft_refresh_interval_hours=int(os.getenv("AIRCRAFT_REFRESH_INTERVAL_HOURS", "168")),
            airport_refresh_interval_hours=int(os.getenv("AIRPORT_REFRESH_INTERVAL_HOURS", "720")),
            failed_source_retry_hours=int(os.getenv("FAILED_SOURCE_RETRY_HOURS", "1")),
            opensky_seed_retry_attempts=int(os.getenv("OPENSKY_SEED_RETRY_ATTEMPTS", "3")),
            opensky_seed_retry_base_delay_seconds=float(
                os.getenv("OPENSKY_SEED_RETRY_BASE_DELAY_SECONDS", "1.0")
            ),
            data_seed_batch_size=int(os.getenv("DATA_SEED_BATCH_SIZE", "1000")),
            jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-me-in-production"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expiry_days=int(os.getenv("JWT_EXPIRY_DAYS", "30")),
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            smtp_from_email=os.getenv("SMTP_FROM_EMAIL", "noreply@example.com"),
            app_base_url=os.getenv("APP_BASE_URL", "http://localhost:5173"),
            google_client_id=os.getenv("GOOGLE_CLIENT_ID"),
            providers_config_path=os.getenv("PROVIDERS_CONFIG_PATH"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=Path(v) if (v := os.getenv("LOG_FILE")) else None,
            log_max_bytes=int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024))),
            log_backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
            admin_email=os.getenv("ADMIN_EMAIL", "admin@chemtrail-tracker.com"),
            admin_password=os.getenv("ADMIN_PASSWORD", "change-me-admin-password"),
            ai_provider=os.getenv("AI_PROVIDER", "deepseek"),
            ai_model=os.getenv("AI_MODEL", "deepseek-chat"),
            ai_api_key=os.getenv("AI_API_KEY"),
            ai_base_url=os.getenv("AI_BASE_URL"),
            auto_block_requests_per_minute=int(os.getenv("AUTO_BLOCK_REQUESTS_PER_MINUTE", "300")),
            auto_block_release_hours=int(os.getenv("AUTO_BLOCK_RELEASE_HOURS", "24")),
        )

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings.from_env()
    settings.ensure_directories()
    return settings
