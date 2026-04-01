from __future__ import annotations

import mimetypes
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.db import get_db
from app.dependencies import get_app_settings, get_enrichment_service, get_image_storage_service
from app.models import AircraftRegistry, FlightLog, FlightLogPhoto
from app.serializers import resolve_log_coordinates, serialize_flight_log, serialize_nearby_log
from app.schemas import (
    FlightLogCreate,
    FlightLogResponse,
    LoggedFlightNearbyResponse,
    parse_time_window,
)
from app.services.aircraft_enrichment import AircraftEnrichmentService
from app.services.image_storage import ImageStorageError, ImageStorageService, UnsupportedImageError
from app.utils.geo import center_from_bounds, haversine_distance_km, radius_from_bounds


router = APIRouter(prefix="/logs", tags=["logs"])
photo_router = APIRouter(tags=["photos"])


def parse_log_form(
    icao24: str = Form(...),
    callsign: str | None = Form(None),
    origin_country: str | None = Form(None),
    departure_airport: str | None = Form(None),
    arrival_airport: str | None = Form(None),
    aircraft_latitude: str | None = Form(None),
    aircraft_longitude: str | None = Form(None),
    altitude: float | None = Form(None),
    velocity: float | None = Form(None),
    heading: float | None = Form(None),
    vertical_rate: float | None = Form(None),
    owner_uuid: str | None = Form(None),
    logger_name: str | None = Form(None),
    logger_location: str | None = Form(None),
    logger_latitude: str | None = Form(None),
    logger_longitude: str | None = Form(None),
    note: str | None = Form(None),
) -> FlightLogCreate:
    try:
        return FlightLogCreate(
            icao24=icao24,
            callsign=callsign,
            origin_country=origin_country,
            departure_airport=departure_airport,
            arrival_airport=arrival_airport,
            aircraft_latitude=aircraft_latitude,
            aircraft_longitude=aircraft_longitude,
            altitude=altitude,
            velocity=velocity,
            heading=heading,
            vertical_rate=vertical_rate,
            owner_uuid=owner_uuid,
            logger_name=logger_name,
            logger_location=logger_location,
            logger_latitude=logger_latitude,
            logger_longitude=logger_longitude,
            note=note,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("", response_model=FlightLogResponse, status_code=201)
async def create_log(
    payload: FlightLogCreate = Depends(parse_log_form),
    photos: list[UploadFile] | None = File(default=None),
    db_session: Session = Depends(get_db),
    enrichment_service: AircraftEnrichmentService = Depends(get_enrichment_service),
    image_storage: ImageStorageService = Depends(get_image_storage_service),
) -> FlightLogResponse:
    uploads = photos or []
    if len(uploads) > 3:
        raise HTTPException(status_code=400, detail="A maximum of 3 photos is allowed")

    stored_images = []
    registry = None
    try:
        flight_log = FlightLog(**payload.model_dump())
        db_session.add(flight_log)
        db_session.flush()

        registry = enrichment_service.enrich(db_session, payload.icao24)
        stored_images = await image_storage.save_uploads(flight_log.id, uploads)
        for stored_image in stored_images:
            flight_log.photos.append(FlightLogPhoto(file_path=stored_image.relative_path))

        db_session.flush()
        db_session.commit()
    except UnsupportedImageError as exc:
        db_session.rollback()
        image_storage.cleanup(stored_images)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImageStorageError as exc:
        db_session.rollback()
        image_storage.cleanup(stored_images)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db_session.rollback()
        image_storage.cleanup(stored_images)
        raise HTTPException(status_code=500, detail="Database persistence failed") from exc
    except Exception as exc:
        db_session.rollback()
        image_storage.cleanup(stored_images)
        raise HTTPException(status_code=500, detail="Unexpected error while creating flight log") from exc

    db_session.refresh(flight_log)
    return serialize_flight_log(flight_log, registry)


@router.get("/nearby", response_model=list[LoggedFlightNearbyResponse])
def get_nearby_logs(
    north: float = Query(...),
    south: float = Query(...),
    east: float = Query(...),
    west: float = Query(...),
    time_window: str = Query("1d"),
    viewer_uuid: str | None = Query(None),
    settings: Settings = Depends(get_app_settings),
    db_session: Session = Depends(get_db),
) -> list[LoggedFlightNearbyResponse]:
    if south >= north:
        raise HTTPException(status_code=422, detail="south must be less than north")
    if west >= east:
        raise HTTPException(status_code=422, detail="west must be less than east")
    if radius_from_bounds(north, south, east, west) > settings.max_nearby_radius_km:
        raise HTTPException(
            status_code=422,
            detail=f"requested bounds exceed the maximum nearby radius of {settings.max_nearby_radius_km} km",
        )

    try:
        window = parse_time_window(time_window)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    cutoff = datetime.now(timezone.utc) - window
    logs = db_session.execute(
        select(FlightLog)
        .options(selectinload(FlightLog.photos))
        .where(FlightLog.created_at >= cutoff)
    ).scalars()
    log_items = list(logs)
    center_lat, center_lon = center_from_bounds(north, south, east, west)
    icao24s = sorted({log.icao24 for log in log_items})
    registry_map: dict[str, AircraftRegistry] = {}
    if icao24s:
        registry_rows = db_session.execute(
            select(AircraftRegistry).where(AircraftRegistry.icao24.in_(icao24s))
        ).scalars()
        registry_map = {row.icao24: row for row in registry_rows}

    results: list[LoggedFlightNearbyResponse] = []
    for log in log_items:
        coordinates = resolve_log_coordinates(log)
        if coordinates is None:
            continue
        if not (south <= coordinates[0] <= north and west <= coordinates[1] <= east):
            continue
        distance_km = round(haversine_distance_km(center_lat, center_lon, coordinates[0], coordinates[1]), 3)
        results.append(
            serialize_nearby_log(
                log=log,
                distance_km=distance_km,
                viewer_uuid=viewer_uuid,
                registry=registry_map.get(log.icao24),
            )
        )

    results.sort(key=lambda item: (item.distance_km, -item.created_at.timestamp()))
    return results


@photo_router.get("/photos/{photo_id}")
def get_photo(
    photo_id: int,
    db_session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    photo = db_session.get(FlightLogPhoto, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")

    path = settings.upload_dir / photo.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Photo file not found")

    media_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=media_type or "application/octet-stream")
