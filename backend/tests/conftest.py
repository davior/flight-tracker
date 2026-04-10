from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    upload_dir = tmp_path / "uploads"
    runtime_dir = tmp_path / "runtime"
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_dir=upload_dir,
        runtime_dir=runtime_dir,
        max_nearby_radius_km=500,
        live_flight_provider="opensky",
        opensky_client_id=None,
        opensky_client_secret=None,
        adsbx_api_key="demo-key",
        jwt_secret_key="test-secret-key",
    )


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)
