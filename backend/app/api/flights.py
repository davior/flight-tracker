from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_app_settings, get_opensky_client
from app.models import AircraftRegistry
from app.schemas import NearbyFlightResponse, build_display_type
from app.services.opensky import OpenSkyClient, OpenSkyError


router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("/nearby", response_model=list[NearbyFlightResponse])
def get_nearby_flights(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(20.0, gt=0),
    settings=Depends(get_app_settings),
    opensky_client: OpenSkyClient = Depends(get_opensky_client),
    db_session: Session = Depends(get_db),
) -> list[NearbyFlightResponse]:
    if radius_km > settings.max_nearby_radius_km:
        raise HTTPException(
            status_code=422,
            detail=f"radius_km must be less than or equal to {settings.max_nearby_radius_km}",
        )

    try:
        flights = opensky_client.get_nearby_flights(lat=lat, lon=lon, radius_km=radius_km)
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

    enriched: list[NearbyFlightResponse] = []
    for flight in flights:
        registry = registry_map.get(flight.icao24)
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
                category=registry.category if registry else None,
                display_type=build_display_type(
                    type_code=registry.type_code if registry else None,
                    manufacturer=registry.manufacturer if registry else None,
                    model=registry.model if registry else None,
                    category=registry.category if registry else None,
                ),
            )
        )
    return enriched
