from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_app_settings, get_enrichment_queue, get_live_flight_provider
from app.models import AircraftRegistry
from app.schemas import LiveFlightCapabilitiesResponse, NearbyFlightResponse, ProviderStatusItem, ProviderStatusResponse, TrajectoryResponse, build_display_type, normalize_icao24
from app.services.aircraft_categories import load_aircraft_category_map, resolve_aircraft_category_details
from app.services.aircraft_enrichment_queue import AircraftEnrichmentQueue
from app.services.live_flight_provider import LiveFlightProvider, LiveFlightProviderError
from app.services.provider_router import ProviderRouter
from app.services.trajectory import build_trajectory
from app.utils.geo import radius_from_bounds


router = APIRouter(prefix="/flights", tags=["flights"])
MAX_HISTORY_MINUTES = 60
HISTORY_STEP_MINUTES = 1
TRAJECTORY_DEFAULT_MAX_HISTORY_MINUTES = 60
TRAJECTORY_DEFAULT_STEP_MINUTES = 10


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


@router.get("/provider-status", response_model=ProviderStatusResponse)
def get_provider_status(
    live_flight_provider: LiveFlightProvider = Depends(get_live_flight_provider),
) -> ProviderStatusResponse:
    if not isinstance(live_flight_provider, ProviderRouter):
        # Defensive fallback — should always be a ProviderRouter at runtime
        caps = live_flight_provider.capabilities
        return ProviderStatusResponse(
            active_provider=caps.provider,
            providers=[
                ProviderStatusItem(
                    name=caps.provider,
                    is_active=True,
                    is_healthy=True,
                    requests_in_period=0,
                    max_requests=None,
                    period_seconds=None,
                    last_request_at=None,
                    last_error_at=None,
                    last_error_code=None,
                    rate_limited_until=None,
                    supports_time_shift=caps.supports_history,
                    supports_trajectory=caps.supports_trajectory,
                )
            ],
        )
    stats = live_flight_provider.get_status()
    return ProviderStatusResponse(
        active_provider=live_flight_provider.active_provider_name,
        providers=[
            ProviderStatusItem(
                name=s.name,
                is_active=s.is_active,
                is_healthy=s.is_healthy,
                requests_in_period=s.requests_in_period,
                max_requests=s.max_requests,
                period_seconds=s.period_seconds,
                last_request_at=s.last_request_at,
                last_error_at=s.last_error_at,
                last_error_code=s.last_error_code,
                rate_limited_until=s.rate_limited_until,
                supports_time_shift=s.supports_time_shift,
                supports_trajectory=s.supports_trajectory,
            )
            for s in stats
        ],
    )


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
                operator=registry.operator if registry else None,
                operator_icao=registry.operator_icao if registry else None,
                operator_callsign=registry.operator_callsign if registry else None,
                owner=registry.owner if registry else None,
                serial_number=registry.serial_number if registry else None,
                year_built=registry.year_built if registry else None,
                engines=registry.engines if registry else None,
                icao_aircraft_type=registry.icao_aircraft_type if registry else None,
            )
        )
    return enriched


@router.get("/{icao24}/trajectory", response_model=TrajectoryResponse)
def get_flight_trajectory(
    icao24: str,
    max_history_minutes: int = Query(default=TRAJECTORY_DEFAULT_MAX_HISTORY_MINUTES, ge=1, le=MAX_HISTORY_MINUTES),
    step_minutes: int = Query(default=TRAJECTORY_DEFAULT_STEP_MINUTES, ge=1, le=10),
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
    reference_time = int(time.time())

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
