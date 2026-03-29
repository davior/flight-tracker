from __future__ import annotations

from decimal import Decimal

from app.models import AircraftRegistry, FlightLog, FlightLogPhoto
from app.schemas import FlightLogResponse, LoggedFlightNearbyResponse, PhotoResponse, build_display_type


def photo_url(photo_id: int) -> str:
    return f"/photos/{photo_id}"


def serialize_photo(photo: FlightLogPhoto) -> PhotoResponse:
    return PhotoResponse(
        id=photo.id,
        file_path=photo.file_path,
        url=photo_url(photo.id),
        created_at=photo.created_at,
    )


def serialize_flight_log(log: FlightLog, registry: AircraftRegistry | None = None) -> FlightLogResponse:
    return FlightLogResponse(
        id=log.id,
        created_at=log.created_at,
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
        category=registry.category if registry else None,
        display_type=build_display_type(
            type_code=registry.type_code if registry else None,
            manufacturer=registry.manufacturer if registry else None,
            model=registry.model if registry else None,
            category=registry.category if registry else None,
        ),
        photos=[serialize_photo(photo) for photo in log.photos],
        aircraft_registry=registry,
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
) -> LoggedFlightNearbyResponse:
    return LoggedFlightNearbyResponse(
        id=log.id,
        created_at=log.created_at,
        icao24=log.icao24,
        callsign=log.callsign,
        note=log.note,
        aircraft_latitude=log.aircraft_latitude,
        aircraft_longitude=log.aircraft_longitude,
        logger_latitude=log.logger_latitude,
        logger_longitude=log.logger_longitude,
        owner_uuid=log.owner_uuid,
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
        photos=[serialize_photo(photo) for photo in log.photos],
        distance_km=distance_km,
        is_owner=viewer_uuid is not None and log.owner_uuid == viewer_uuid,
    )
