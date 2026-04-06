from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_app_settings, get_enrichment_queue, get_live_flight_provider
from app.models import AircraftRegistry
from app.schemas import LiveFlightCapabilitiesResponse, NearbyFlightResponse, TrajectoryResponse, build_display_type, normalize_icao24
from app.services.aircraft_categories import load_aircraft_category_map, resolve_aircraft_category_details
from app.services.aircraft_enrichment_queue import AircraftEnrichmentQueue
from app.services.live_flight_provider import LiveFlightProvider, LiveFlightProviderError
from app.services.trajectory import build_trajectory
from app.utils.geo import radius_from_bounds


router = APIRouter(prefix="/flights", tags=["flights"])
MAX_HISTORY_MINUTES = 60
HISTORY_STEP_MINUTES = 1
TRAJECTORY_DEFAULT_MAX_HISTORY_MINUTES = 30
TRAJECTORY_DEFAULT_STEP_MINUTES = 2


def resolve_time_shift_seconds(time_shift_minutes: int) -> int | None:
    if time_shift_minutes == 0:
        return None

    shifted_time_seconds = int(time.time()) - (time_shift_minutes * 60)
    return shifted_time_seconds - (shifted_time_seconds % 5)


@router.get("/capabilities", response_model=LiveFlightCapabilitiesResponse)
def get_live_flight_capabilities(
    live_flight_provider: LiveFlightProvider = Depends(get_live_flight_provider),
) -> LiveFlightCapabilitiesResponse:
    return LiveFlightCapabilitiesResponse.model_validate(live_flight_provider.capabilities)


@router.get("/nearby", response_model=list[NearbyFlightResponse])
def get_nearby_flights(
    north: float = Query(...),
    south: float = Query(...),
    east: float = Query(...),
    west: float = Query(...),
    time_shift_minutes: int = 0,
    settings=Depends(get_app_settings),
    live_flight_provider: LiveFlightProvider = Depends(get_live_flight_provider),
    enrichment_queue: AircraftEnrichmentQueue = Depends(get_enrichment_queue),
    db_session: Session = Depends(get_db),
) -> list[NearbyFlightResponse]:
    if south >= north:
        raise HTTPException(
            status_code=422,
            detail="south must be less than north",
        )
    if west >= east:
        raise HTTPException(status_code=422, detail="west must be less than east")
    if radius_from_bounds(north, south, east, west) > settings.max_nearby_radius_km:
        raise HTTPException(
            status_code=422,
            detail=f"requested bounds exceed the maximum nearby radius of {settings.max_nearby_radius_km} km",
        )
    if time_shift_minutes < 0 or time_shift_minutes > MAX_HISTORY_MINUTES:
        raise HTTPException(
            status_code=422,
            detail=f"time_shift_minutes must be between 0 and {MAX_HISTORY_MINUTES}",
        )
    capabilities = live_flight_provider.capabilities
    if time_shift_minutes > capabilities.max_history_minutes:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "live_history_unavailable",
                "message": "Historical live positions are unavailable for the configured live provider.",
                "provider": capabilities.provider,
            },
        )

    time_seconds = resolve_time_shift_seconds(time_shift_minutes)

    try:
        flights = live_flight_provider.get_flights_in_bounds(
            north=north,
            south=south,
            east=east,
            west=west,
            time_seconds=time_seconds,
        )
    except LiveFlightProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "live_provider_unavailable",
                "message": str(exc),
                "provider": exc.provider,
                "reason": exc.code,
            },
        ) from exc

    icao24s = [flight.icao24 for flight in flights]
    registry_map: dict[str, AircraftRegistry] = {}
    if icao24s:
        registry_rows = db_session.execute(
            select(AircraftRegistry).where(AircraftRegistry.icao24.in_(icao24s))
        ).scalars()
        registry_map = {row.icao24: row for row in registry_rows}

    missing_icao24s = list(dict.fromkeys(icao24 for icao24 in icao24s if icao24 not in registry_map))
    if missing_icao24s:
        enrichment_queue.enqueue_many(missing_icao24s)

    category_map = load_aircraft_category_map(
        db_session,
        (registry.category for registry in registry_map.values()),
    )

    enriched: list[NearbyFlightResponse] = []
    for flight in flights:
        registry = registry_map.get(flight.icao24)
        category_code, category_label, category_description = resolve_aircraft_category_details(
            registry.category if registry else None,
            category_map,
        )
        enriched.append(
            NearbyFlightResponse(
                icao24=flight.icao24,
                callsign=flight.callsign,
                origin_country=flight.origin_country,
                latitude=flight.latitude,
                longitude=flight.longitude,
                altitude=flight.altitude,
                velocity=flight.velocity,
                heading=flight.heading,
                vertical_rate=flight.vertical_rate,
                last_contact=flight.last_contact,
                distance_km=flight.distance_km,
                type_code=registry.type_code if registry else None,
                manufacturer=registry.manufacturer if registry else None,
                model=registry.model if registry else None,
                category=category_code,
                category_label=category_label,
                category_description=category_description,
                display_type=build_display_type(
                    type_code=registry.type_code if registry else None,
                    manufacturer=registry.manufacturer if registry else None,
                    model=registry.model if registry else None,
                    category=category_code,
                    category_label=category_label,
                ),
            )
        )
    return enriched


@router.get("/{icao24}/trajectory", response_model=TrajectoryResponse)
def get_flight_trajectory(
    icao24: str,
    max_history_minutes: int = Query(default=TRAJECTORY_DEFAULT_MAX_HISTORY_MINUTES, ge=1, le=MAX_HISTORY_MINUTES),
    step_minutes: int = Query(default=TRAJECTORY_DEFAULT_STEP_MINUTES, ge=1, le=10),
    time_shift_minutes: int = Query(default=0, ge=0, le=MAX_HISTORY_MINUTES),
    live_flight_provider: LiveFlightProvider = Depends(get_live_flight_provider),
) -> TrajectoryResponse:
    try:
        normalized = normalize_icao24(icao24)
    except ValueError:
        raise HTTPException(status_code=422, detail="icao24 must be a 6-character hexadecimal string")

    capabilities = live_flight_provider.capabilities
    if not capabilities.supports_history:
        return TrajectoryResponse(icao24=normalized, supports_trajectory=False, points=[])

    effective_max = min(max_history_minutes, capabilities.max_history_minutes)
    reference_time = resolve_time_shift_seconds(time_shift_minutes) or int(time.time())

    try:
        points = build_trajectory(
            provider=live_flight_provider,
            icao24=normalized,
            reference_time=reference_time,
            max_history_minutes=effective_max,
            step_minutes=step_minutes,
        )
    except LiveFlightProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "live_provider_unavailable",
                "message": str(exc),
                "provider": exc.provider,
                "reason": exc.code,
            },
        ) from exc

    return TrajectoryResponse(icao24=normalized, supports_trajectory=True, points=points)
