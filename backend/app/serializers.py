from __future__ import annotations

from decimal import Decimal

from app.models import AircraftCategory, AircraftRegistry, FlightLog, FlightLogPhoto
from app.schemas import (
    AircraftRegistryResponse,
    FlightLogResponse,
    LoggedFlightNearbyResponse,
    PhotoResponse,
    TrajectoryPoint,
    build_display_type,
)
from app.services.aircraft_categories import resolve_aircraft_category_details


def photo_url(photo_id: int) -> str:
    return f"/photos/{photo_id}"


def serialize_photo(photo: FlightLogPhoto) -> PhotoResponse:
    return PhotoResponse(
        id=photo.id,
        file_path=photo.file_path,
        url=photo_url(photo.id),
        created_at=photo.created_at,
    )


def serialize_aircraft_registry(
    registry: AircraftRegistry,
    category: AircraftCategory | None = None,
) -> AircraftRegistryResponse:
    category_code, category_label, category_description = resolve_aircraft_category_details(
        registry.category,
        {category.code: category} if category is not None else {},
    )
    return AircraftRegistryResponse(
        icao24=registry.icao24,
        registration=registry.registration,
        type_code=registry.type_code,
        manufacturer=registry.manufacturer,
        model=registry.model,
        category=category_code,
        category_label=category_label,
        category_description=category_description,
        first_seen=registry.first_seen,
        last_updated=registry.last_updated,
    )


def serialize_flight_log(
    log: FlightLog,
    registry: AircraftRegistry | None = None,
    category: AircraftCategory | None = None,
) -> FlightLogResponse:
    category_code, category_label, category_description = resolve_aircraft_category_details(
        registry.category if registry else None,
        {category.code: category} if category is not None else {},
    )
    return FlightLogResponse(
        id=log.id,
        created_at=log.created_at,
        flight_time=log.flight_time,
        icao24=log.icao24,
        callsign=log.callsign,
        origin_country=log.origin_country,
        departure_airport=log.departure_airport,
        arrival_airport=log.arrival_airport,
        aircraft_latitude=log.aircraft_latitude,
        aircraft_longitude=log.aircraft_longitude,
        altitude=log.altitude,
        velocity=log.velocity,
        heading=log.heading,
        vertical_rate=log.vertical_rate,
        owner_uuid=log.owner_uuid,
        logger_name=log.logger_name,
        logger_location=log.logger_location,
        logger_latitude=log.logger_latitude,
        logger_longitude=log.logger_longitude,
        note=log.note,
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
        photos=[serialize_photo(photo) for photo in log.photos],
        aircraft_registry=serialize_aircraft_registry(registry, category) if registry else None,
        trajectory=[TrajectoryPoint.model_validate(p) for p in log.trajectory] if log.trajectory else None,
    )


def resolve_log_coordinates(log: FlightLog) -> tuple[float, float] | None:
    if log.aircraft_latitude is not None and log.aircraft_longitude is not None:
        return float(log.aircraft_latitude), float(log.aircraft_longitude)
    if log.logger_latitude is not None and log.logger_longitude is not None:
        return float(log.logger_latitude), float(log.logger_longitude)
    return None


def serialize_nearby_log(
    log: FlightLog,
    distance_km: float,
    viewer_uuid: str | None,
    registry: AircraftRegistry | None = None,
    category: AircraftCategory | None = None,
) -> LoggedFlightNearbyResponse:
    category_code, category_label, category_description = resolve_aircraft_category_details(
        registry.category if registry else None,
        {category.code: category} if category is not None else {},
    )
    return LoggedFlightNearbyResponse(
        id=log.id,
        created_at=log.created_at,
        flight_time=log.flight_time,
        icao24=log.icao24,
        callsign=log.callsign,
        note=log.note,
        aircraft_latitude=log.aircraft_latitude,
        aircraft_longitude=log.aircraft_longitude,
        logger_latitude=log.logger_latitude,
        logger_longitude=log.logger_longitude,
        owner_uuid=log.owner_uuid,
        heading=log.heading,
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
        photos=[serialize_photo(photo) for photo in log.photos],
        distance_km=distance_km,
        is_owner=viewer_uuid is not None and log.owner_uuid == viewer_uuid,
        trajectory=[TrajectoryPoint.model_validate(p) for p in log.trajectory] if log.trajectory else None,
    )
