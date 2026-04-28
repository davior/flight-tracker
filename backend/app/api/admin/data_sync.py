from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_admin, get_data_seeder
from app.models import DataSyncLog
from app.schemas import DataSyncStatusResponse, DataSyncTriggerResponse
from app.services.data_seeder import (
    DataSeeder,
    SOURCE_FAA_AIRCRAFT,
    SOURCE_OPENFLIGHTS_ROUTES,
    SOURCE_OPENSKY_AIRCRAFT,
    SOURCE_OPENSKY_ROUTES,
    SOURCE_OURAIRPORTS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-sync", tags=["admin-data-sync"])

_VALID_SOURCES = {
    SOURCE_OPENSKY_AIRCRAFT,
    SOURCE_FAA_AIRCRAFT,
    SOURCE_OURAIRPORTS,
    SOURCE_OPENSKY_ROUTES,
    SOURCE_OPENFLIGHTS_ROUTES,
}

_SOURCE_SEED_METHOD = {
    SOURCE_OPENSKY_AIRCRAFT: "seed_opensky_aircraft",
    SOURCE_FAA_AIRCRAFT: "seed_faa_aircraft",
    SOURCE_OURAIRPORTS: "seed_airports",
    SOURCE_OPENSKY_ROUTES: "seed_routes",
    SOURCE_OPENFLIGHTS_ROUTES: "seed_openflights_routes",
}


@router.get("", response_model=list[DataSyncStatusResponse])
def list_sync_status(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    return db.query(DataSyncLog).order_by(DataSyncLog.source).all()


@router.post("/{source}/trigger", response_model=DataSyncTriggerResponse)
def trigger_sync(
    source: str,
    background_tasks: BackgroundTasks,
    seeder: DataSeeder = Depends(get_data_seeder),
    _admin=Depends(get_current_admin),
):
    if source not in _VALID_SOURCES:
        raise HTTPException(status_code=404, detail=f"Unknown source '{source}'")
    method_name = _SOURCE_SEED_METHOD[source]
    method = getattr(seeder, method_name, None)
    if method is None:
        raise HTTPException(status_code=500, detail="Seed method not found")

    def _run():
        try:
            method()
            logger.info("Manual sync completed: %s", source)
        except Exception:
            logger.exception("Manual sync failed: %s", source)

    background_tasks.add_task(_run)
    return DataSyncTriggerResponse(source=source, message=f"Sync triggered for '{source}' in background")


@router.post("/upload/{source}")
async def upload_file(
    source: str,
    file: UploadFile = File(...),
    seeder: DataSeeder = Depends(get_data_seeder),
    _admin=Depends(get_current_admin),
):
    """Accept a manual file upload and run the corresponding seeder against it."""
    if source not in _VALID_SOURCES:
        raise HTTPException(status_code=404, detail=f"Unknown source '{source}'")

    import tempfile, os

    content = await file.read()
    suffix = "." + (file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    method_name = _SOURCE_SEED_METHOD[source]
    method = getattr(seeder, method_name, None)
    if method is None:
        os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail="Seed method not found")

    def _run():
        try:
            # Pass the file path as override where the seeder supports it
            try:
                method(file_path=tmp_path)
            except TypeError:
                method()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run)
    return {"message": f"File loaded for '{source}'"}
