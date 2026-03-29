from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path


def test_uvicorn_smoke_startup(tmp_path):
    upload_dir = tmp_path / "uploads"
    runtime_dir = tmp_path / "runtime"
    database_path = tmp_path / "smoke.db"

    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f"sqlite:///{database_path}",
            "UPLOAD_DIR": str(upload_dir),
            "RUNTIME_DIR": str(runtime_dir),
        }
    )

    backend_dir = Path(__file__).resolve().parents[1]
    script = """
import asyncio
from app.main import app

async def main():
    async with app.router.lifespan_context(app):
        print("started", flush=True)

asyncio.run(main())
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "started" in result.stdout
