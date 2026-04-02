from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_app_settings, get_enrichment_queue, get_opensky_client
from app.models import AircraftRegistry
from app.schemas import NearbyFlightResponse, build_display_type
from app.services.aircraft_categories import load_aircraft_category_map, resolve_aircraft_category_details
from app.services.aircraft_enrichment_queue import AircraftEnrichmentQueue
from app.services.opensky import OpenSkyClient, OpenSkyError
from app.utils.geo import radius_from_bounds


router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("/nearby", response_model=list[NearbyFlightResponse])
def get_nearby_flights(
    north: float = Query(...),
    south: float = Query(...),
    east: float = Query(...),
    west: float = Query(...),
    settings=Depends(get_app_settings),
    opensky_client: OpenSkyClient = Depends(get_opensky_client),
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

    try:
        flights = opensky_client.get_flights_in_bounds(north=north, south=south, east=east, west=west)
    except OpenSkyError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "opensky_unavailable", "message": str(exc)},
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
